import { useParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { getDescendantsSvg, getDescendantsHierarchy } from "../services/api";

function Tree() {
    const { id } = useParams()
    const containerRef = useRef()
    const [svgContent, setSvgContent] = useState(null)
    const [treeName, setTreeName] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        Promise.all([
            getDescendantsSvg(id, 10),
            getDescendantsHierarchy(id, 1).then(h => h.name).catch(() => null)
        ])
            .then(([svg, name]) => {
                setSvgContent(svg)
                setTreeName(name)
                setLoading(false)
            })
            .catch(err => {
                console.error(err)
                setLoading(false)
            })
    }, [id])

    useEffect(() => {
        if (!svgContent || !containerRef.current) return

        const container = containerRef.current
        container.innerHTML = svgContent

        // Add zoom/pan to the server-rendered SVG
        const svg = d3.select(container).select('svg')
        if (svg.empty()) return

        svg.attr('width', '100%').style('cursor', 'grab')

        const g = svg.select('g')
        if (g.empty()) return

        const zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', function(event) {
                g.attr('transform', event.transform)
            })

        svg.call(zoom)
    }, [svgContent])

    if (loading) return <div className="page">Loading...</div>
    if (!svgContent) return <div className="page">No data found</div>

    return (
        <div className="page">
            {treeName && <h1>Descendants of {treeName}</h1>}
            <div ref={containerRef}></div>
        </div>
    )
}

export default Tree;
