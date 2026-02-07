package com.familytree.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.w3c.dom.*;
import org.xml.sax.InputSource;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.StringReader;
import java.io.StringWriter;
import java.util.Map;

/**
 * Service to overlay avatar images onto SVG tree visualizations.
 *
 * The D3 service renders trees with colored circles and initials.
 * This service post-processes the SVG to inject actual avatar images
 * for persons who have them, creating circular-clipped photos with
 * the gender-colored circle as a border.
 *
 * Avatars are embedded as base64 data URLs to work when SVG is used
 * as an img src (which blocks external resources for security).
 */
@Service
public class AvatarOverlayService {

    private static final Logger log = LoggerFactory.getLogger(AvatarOverlayService.class);
    private static final String SVG_NS = "http://www.w3.org/2000/svg";

    /**
     * Overlay avatar images onto SVG nodes that have avatars.
     * Avatars should be provided as base64 data URLs for embedding.
     *
     * @param svgContent    The raw SVG content from D3 service
     * @param personAvatars Map of personId to base64 data URL (e.g., "data:image/jpeg;base64,...")
     * @param nodeRadius    The radius of node circles in the SVG (e.g., 48 for MRCA, 8 for ancestors/descendants)
     * @return Modified SVG with avatar images embedded
     */
    public String overlayAvatars(String svgContent, Map<Long, String> personAvatars, int nodeRadius) {
        if (personAvatars == null || personAvatars.isEmpty()) {
            return svgContent;
        }

        try {
            Document doc = parseXml(svgContent);

            // Ensure clipPath definitions exist for each avatar
            ensureClipPaths(doc, personAvatars, nodeRadius);

            // Find all node groups and process them
            NodeList nodes = doc.getElementsByTagName("g");
            for (int i = 0; i < nodes.getLength(); i++) {
                Element node = (Element) nodes.item(i);

                // Check if this is a node group with a person ID
                if (!"node".equals(node.getAttribute("class"))) {
                    continue;
                }

                String personIdStr = node.getAttribute("data-person-id");
                if (personIdStr == null || personIdStr.isEmpty()) {
                    continue;
                }

                try {
                    Long personId = Long.parseLong(personIdStr);
                    String avatarDataUrl = personAvatars.get(personId);

                    if (avatarDataUrl != null) {
                        addAvatarToNode(doc, node, personId, avatarDataUrl, nodeRadius);
                    }
                } catch (NumberFormatException e) {
                    log.warn("Invalid person ID: {}", personIdStr);
                }
            }

            return serializeXml(doc);

        } catch (Exception e) {
            log.error("Failed to parse/modify SVG, returning original", e);
            return svgContent;
        }
    }

    /**
     * Parse SVG string as XML document.
     */
    private Document parseXml(String xml) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        DocumentBuilder builder = factory.newDocumentBuilder();
        return builder.parse(new InputSource(new StringReader(xml)));
    }

    /**
     * Serialize XML document back to string.
     */
    private String serializeXml(Document doc) throws Exception {
        TransformerFactory tf = TransformerFactory.newInstance();
        Transformer transformer = tf.newTransformer();
        transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "yes");
        transformer.setOutputProperty(OutputKeys.INDENT, "no");

        StringWriter writer = new StringWriter();
        transformer.transform(new DOMSource(doc), new StreamResult(writer));
        return writer.toString();
    }

    /**
     * Ensure clipPath definitions exist for avatar clipping.
     */
    private void ensureClipPaths(Document doc, Map<Long, String> personAvatars, int nodeRadius) {
        // Find or create defs element
        NodeList defsList = doc.getElementsByTagName("defs");
        Element defs;

        if (defsList.getLength() > 0) {
            defs = (Element) defsList.item(0);
        } else {
            // Create defs element
            defs = doc.createElementNS(SVG_NS, "defs");
            Element svg = doc.getDocumentElement();
            svg.insertBefore(defs, svg.getFirstChild());
        }

        // Add clipPath for each person if not already present
        for (Long personId : personAvatars.keySet()) {
            String clipId = "avatar-clip-" + personId;

            // Check if clipPath already exists
            if (doc.getElementById(clipId) != null) {
                continue;
            }

            // Create clipPath element
            Element clipPath = doc.createElementNS(SVG_NS, "clipPath");
            clipPath.setAttribute("id", clipId);

            Element circle = doc.createElementNS(SVG_NS, "circle");
            circle.setAttribute("r", String.valueOf(nodeRadius));
            circle.setAttribute("cx", "0");
            circle.setAttribute("cy", "0");

            clipPath.appendChild(circle);
            defs.appendChild(clipPath);
        }
    }

    /**
     * Make SVG nodes clickable by wrapping them in anchor tags.
     * Also adds hover styles for visual feedback.
     *
     * @param svgContent The SVG content to modify
     * @return Modified SVG with clickable nodes
     */
    public String makeNodesClickable(String svgContent) {
        try {
            Document doc = parseXml(svgContent);

            // Add hover styles
            addHoverStyles(doc);

            // Find all node groups and wrap them in links
            NodeList nodes = doc.getElementsByTagName("g");
            // Collect nodes first to avoid modifying while iterating
            java.util.List<Element> nodeElements = new java.util.ArrayList<>();
            for (int i = 0; i < nodes.getLength(); i++) {
                Element node = (Element) nodes.item(i);
                if ("node".equals(node.getAttribute("class"))) {
                    nodeElements.add(node);
                }
            }

            for (Element node : nodeElements) {
                String personIdStr = node.getAttribute("data-person-id");
                if (personIdStr == null || personIdStr.isEmpty()) {
                    continue;
                }

                // Add cursor style to node
                String existingStyle = node.getAttribute("style");
                String cursorStyle = "cursor: pointer;";
                if (existingStyle != null && !existingStyle.isEmpty()) {
                    node.setAttribute("style", existingStyle + " " + cursorStyle);
                } else {
                    node.setAttribute("style", cursorStyle);
                }

                // Create anchor element
                Element anchor = doc.createElementNS(SVG_NS, "a");
                anchor.setAttribute("href", "/person/" + personIdStr);
                anchor.setAttribute("target", "_top");

                // Replace node with anchor containing node
                Node parent = node.getParentNode();
                parent.insertBefore(anchor, node);
                parent.removeChild(node);
                anchor.appendChild(node);
            }

            return serializeXml(doc);

        } catch (Exception e) {
            log.error("Failed to make nodes clickable, returning original", e);
            return svgContent;
        }
    }

    /**
     * Add CSS hover styles to the SVG defs section.
     */
    private void addHoverStyles(Document doc) {
        // Find or create defs element
        NodeList defsList = doc.getElementsByTagName("defs");
        Element defs;

        if (defsList.getLength() > 0) {
            defs = (Element) defsList.item(0);
        } else {
            defs = doc.createElementNS(SVG_NS, "defs");
            Element svg = doc.getDocumentElement();
            svg.insertBefore(defs, svg.getFirstChild());
        }

        // Create style element with hover effects
        Element style = doc.createElementNS(SVG_NS, "style");
        style.setTextContent(
            "a:hover g.node { opacity: 0.85; }" +
            "a:hover g.node circle { stroke-width: 5; stroke: #fff; }"
        );
        defs.insertBefore(style, defs.getFirstChild());
    }

    /**
     * Add avatar image to a node, keeping the circle as a border.
     */
    private void addAvatarToNode(Document doc, Element node, Long personId, String avatarDataUrl, int nodeRadius) {
        String clipId = "avatar-clip-" + personId;

        // Remove any existing image elements
        NodeList images = node.getElementsByTagName("image");
        while (images.getLength() > 0) {
            images.item(0).getParentNode().removeChild(images.item(0));
        }

        // Remove initials text (white bold text centered in MRCA circles) but preserve
        // name labels used in ancestors/descendants trees (which have fill="#333")
        NodeList texts = node.getElementsByTagName("text");
        for (int i = texts.getLength() - 1; i >= 0; i--) {
            Element text = (Element) texts.item(i);
            if ("0.35em".equals(text.getAttribute("dy")) && "#fff".equals(text.getAttribute("fill"))) {
                text.getParentNode().removeChild(text);
            }
        }

        // Find the circle element to insert after
        NodeList circles = node.getElementsByTagName("circle");
        if (circles.getLength() == 0) {
            log.warn("No circle found in node for person {}", personId);
            return;
        }
        Element circle = (Element) circles.item(0);

        // Create image element
        Element image = doc.createElementNS(SVG_NS, "image");
        image.setAttribute("href", avatarDataUrl);
        image.setAttribute("x", String.valueOf(-nodeRadius));
        image.setAttribute("y", String.valueOf(-nodeRadius));
        image.setAttribute("width", String.valueOf(nodeRadius * 2));
        image.setAttribute("height", String.valueOf(nodeRadius * 2));
        image.setAttribute("clip-path", "url(#" + clipId + ")");
        image.setAttribute("preserveAspectRatio", "xMidYMid slice");

        // Insert image after circle
        Node nextSibling = circle.getNextSibling();
        if (nextSibling != null) {
            node.insertBefore(image, nextSibling);
        } else {
            node.appendChild(image);
        }
    }
}
