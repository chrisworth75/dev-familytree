import {useParams} from "react-router-dom";
import {useEffect, useRef, useState} from "react";
import * as d3 from "d3";

function Tree() {
    const { id } = useParams()
    const svgRef = useRef()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [rootName, setRootName] = useState('')

    const buildHierarchy = (flatData, rootId) => {
        const lookup = {}
        flatData.forEach(function(p) {
            lookup[p.id] = {
                id: p.id,
                firstName: p.firstName,
                surname: p.surname,
                gender: p.gender,
                name: [p.firstName, p.surname].filter(Boolean).join(' '),
                children: []
            }
        })

        flatData.forEach(function(p) {
            const parentId = p.parent1Id || p.parent2Id
            if (parentId && lookup[parentId]) {
                lookup[parentId].children.push(lookup[p.id])
            }
        })

        return lookup[rootId]
    }

    useEffect(() => {
        const rootIdNum = parseInt(id)

        Promise.all([
            fetch('http://localhost:3200/api/person/' + id + '/descendants').then(res => res.json()),
            fetch('http://localhost:3200/api/person/' + id).then(res => res.json())
        ])
            .then(function(results) {
                const descendants = results[0]
                const rootPerson = results[1].person

                const rootNode = {
                    id: rootPerson.id,
                    firstName: rootPerson.firstName,
                    surname: rootPerson.surname,
                    gender: rootPerson.gender,
                    parent1Id: null,
                    parent2Id: null
                }

                const allPeople = [rootNode].concat(descendants)
                const hierarchy = buildHierarchy(allPeople, rootIdNum)
                setData(hierarchy)
                setRootName([rootPerson.firstName, rootPerson.surname].filter(Boolean).join(' '))
                setLoading(false)
            })
            .catch(function(err) {
                console.error(err)
                setLoading(false)
            })
    }, [id])

    useEffect(() => {
        if (!data) return

        const root = d3.hierarchy(data)

        const nodeCount = root.descendants().length
        const depth = root.height
        const width = Math.max(1200, depth * 250)
        const height = Math.max(800, nodeCount * 25)

        d3.select(svgRef.current).selectAll('*').remove()

        const svg = d3.select(svgRef.current)
            .attr('width', '100%')
            .attr('height', height)
            .attr('viewBox', '0 0 ' + width + ' ' + height)
            .style('cursor', 'grab')

        const g = svg.append('g')

        const defs = g.append('defs')

        const zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', function(event) {
                g.attr('transform', event.transform)
            })

        svg.call(zoom)

        const treeLayout = d3.tree().size([height - 100, width - 300])
        treeLayout(root)

        g.attr('transform', 'translate(150, 50)')

        g.selectAll('.link')
            .data(root.links())
            .enter()
            .append('path')
            .attr('class', 'link')
            .attr('d', function(d) {
                return 'M' + d.source.y + ',' + d.source.x +
                    'C' + (d.source.y + d.target.y) / 2 + ',' + d.source.x +
                    ' ' + (d.source.y + d.target.y) / 2 + ',' + d.target.x +
                    ' ' + d.target.y + ',' + d.target.x
            })
            .attr('fill', 'none')
            .attr('stroke', '#ccc')
            .attr('stroke-width', 1.5)

        const nodes = g.selectAll('.node')
            .data(root.descendants())
            .enter()
            .append('g')
            .attr('class', 'node')
            .attr('transform', function(d) { return 'translate(' + d.y + ',' + d.x + ')' })

        nodes.each(function(d) {
            defs.append('clipPath')
                .attr('id', 'clip-' + d.data.id)
                .append('circle')
                .attr('r', 12)
        })

        nodes.append('circle')
            .attr('r', 12)
            .attr('fill', function(d) { return d.data.gender === 'F' ? '#e91e63' : '#2196f3' })

        nodes.append('image')
            .attr('href', function(d) { return 'http://localhost:3200/images/' + d.data.id + '.png' })
            .attr('x', -12)
            .attr('y', -12)
            .attr('width', 24)
            .attr('height', 24)
            .attr('clip-path', function(d) { return 'url(#clip-' + d.data.id + ')' })
            .on('error', function() { d3.select(this).style('display', 'none') })

        nodes.append('text')
            .attr('dy', 4)
            .attr('x', function(d) { return d.children ? -18 : 18 })
            .attr('text-anchor', function(d) { return d.children ? 'end' : 'start' })
            .attr('font-size', '10px')
            .text(function(d) { return d.data.name })

    }, [data])

    if (loading) return <div className="page">Loading...</div>
    if (!data) return <div className="page">No data found</div>

    return (
        <div className="page">
            <h1>Descendants of {rootName}</h1>
            <svg ref={svgRef}></svg>
        </div>
    )
}

export default Tree;
