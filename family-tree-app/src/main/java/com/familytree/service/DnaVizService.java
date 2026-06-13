package com.familytree.service;

import org.springframework.stereotype.Service;

import java.util.Locale;

@Service
public class DnaVizService {

    private static final double MAX_CM = 3400.0;

    private record DnaColor(String primary, String secondary, String label) {
        static DnaColor forCm(double sharedCm) {
            if (sharedCm > 1500) return new DnaColor("#c026d3", "#f0abfc", "Very Close");
            if (sharedCm > 400)  return new DnaColor("#2563eb", "#93c5fd", "Close");
            if (sharedCm > 100)  return new DnaColor("#059669", "#6ee7b7", "Moderate");
            return new DnaColor("#d97706", "#fcd34d", "Distant");
        }
    }

    public String generateChromoBar(double sharedCm, String relationship, Integer segments, int width) {
        DnaColor color = DnaColor.forCm(sharedCm);
        double fillWidth = Math.max(6, (sharedCm / MAX_CM) * width);

        StringBuilder sb = new StringBuilder();
        sb.append(String.format(Locale.US,
                "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"%d\" height=\"50\">", width));

        // Gradient definition
        sb.append(String.format(Locale.US,
                "<defs><linearGradient id=\"cg\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"0\">" +
                "<stop offset=\"0%%\" stop-color=\"%s\"/>" +
                "<stop offset=\"100%%\" stop-color=\"%s\"/>" +
                "</linearGradient></defs>", color.secondary, color.primary));

        // Track
        sb.append(String.format(Locale.US,
                "<rect x=\"0\" y=\"0\" width=\"%d\" height=\"22\" rx=\"11\" fill=\"#f3f4f6\"/>", width));

        // Filled portion
        sb.append(String.format(Locale.US,
                "<rect x=\"0\" y=\"0\" width=\"%.1f\" height=\"22\" rx=\"11\" fill=\"url(#cg)\"/>", fillWidth));

        // Segment lines
        if (segments != null && segments > 0) {
            int lineCount = Math.min(segments, 20);
            for (int i = 1; i < lineCount; i++) {
                double x = (fillWidth / lineCount) * i;
                sb.append(String.format(Locale.US,
                        "<line x1=\"%.1f\" y1=\"3\" x2=\"%.1f\" y2=\"19\" stroke=\"white\" stroke-width=\"1\" opacity=\"0.5\"/>",
                        x, x));
            }
        }

        // Labels
        sb.append(String.format(Locale.US,
                "<text x=\"0\" y=\"38\" font-family=\"system-ui,sans-serif\" font-size=\"11\" fill=\"#6b7280\">%.1f cM</text>",
                sharedCm));

        if (segments != null) {
            sb.append(String.format(Locale.US,
                    "<text x=\"%d\" y=\"38\" font-family=\"system-ui,sans-serif\" font-size=\"11\" fill=\"#6b7280\" text-anchor=\"end\">%d segments</text>",
                    width, segments));
        }

        sb.append("</svg>");
        return sb.toString();
    }

    public String generateStrandCompact(double sharedCm, String relationship) {
        DnaColor color = DnaColor.forCm(sharedCm);
        int dotCount = 20;
        double spacing = 7.2;
        double startX = 4;
        double centreY = 15;
        double radius = 2.8;
        int filled = Math.max(1, (int) Math.round(dotCount * sharedCm / MAX_CM));

        StringBuilder sb = new StringBuilder();
        sb.append("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"150\" height=\"30\">");

        for (int i = 0; i < dotCount; i++) {
            double x = startX + i * spacing;
            double wave = Math.sin(i / 20.0 * Math.PI * 3) * 7;
            double y1 = centreY + wave;
            double y2 = centreY - wave;
            boolean active = i < filled;

            if (active) {
                // Connecting line
                sb.append(String.format(Locale.US,
                        "<line x1=\"%.1f\" y1=\"%.1f\" x2=\"%.1f\" y2=\"%.1f\" stroke=\"%s\" stroke-width=\"1\" opacity=\"0.15\"/>",
                        x, y1, x, y2, color.primary));
                // Top dot
                sb.append(String.format(Locale.US,
                        "<circle cx=\"%.1f\" cy=\"%.1f\" r=\"%.1f\" fill=\"%s\"/>",
                        x, y1, radius, color.primary));
                // Bottom dot
                sb.append(String.format(Locale.US,
                        "<circle cx=\"%.1f\" cy=\"%.1f\" r=\"%.1f\" fill=\"%s\"/>",
                        x, y2, radius, color.secondary));
            } else {
                // Inactive dots
                sb.append(String.format(Locale.US,
                        "<circle cx=\"%.1f\" cy=\"%.1f\" r=\"%.1f\" fill=\"#d1d5db\"/>",
                        x, y1, radius));
                sb.append(String.format(Locale.US,
                        "<circle cx=\"%.1f\" cy=\"%.1f\" r=\"%.1f\" fill=\"#d1d5db\"/>",
                        x, y2, radius));
            }
        }

        sb.append("</svg>");
        return sb.toString();
    }
}
