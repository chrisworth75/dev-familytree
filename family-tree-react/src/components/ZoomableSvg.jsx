import { useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';

function ZoomableSvg({ svgContent, onClick, height = 400 }) {
    const containerRef = useRef();
    const isDraggingRef = useRef(false);

    const handleClick = useCallback((e) => {
        if (isDraggingRef.current) return;
        if (onClick) onClick(e);
    }, [onClick]);

    useEffect(() => {
        if (!svgContent || !containerRef.current) return;

        const container = containerRef.current;
        container.innerHTML = svgContent;

        const svg = d3.select(container).select('svg');
        if (svg.empty()) return;

        svg.attr('width', '100%').attr('height', height).style('cursor', 'grab');

        const g = svg.select('g');
        if (g.empty()) return;

        // Calculate initial fit transform
        const svgNode = svg.node();
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;

        const viewBox = svgNode.getAttribute('viewBox');
        let initialTransform = d3.zoomIdentity;

        if (viewBox) {
            const [, , vbWidth, vbHeight] = viewBox.split(/[\s,]+/).map(Number);
            if (vbWidth && vbHeight) {
                const scale = Math.min(containerWidth / vbWidth, containerHeight / vbHeight, 1);
                const tx = (containerWidth - vbWidth * scale) / 2;
                const ty = (containerHeight - vbHeight * scale) / 2;
                initialTransform = d3.zoomIdentity.translate(tx, ty).scale(scale);
            }
        } else {
            // Fall back to g bounding box
            const gNode = g.node();
            const bbox = gNode.getBBox();
            if (bbox.width && bbox.height) {
                const scale = Math.min(containerWidth / bbox.width, containerHeight / bbox.height, 1) * 0.9;
                const tx = (containerWidth - bbox.width * scale) / 2 - bbox.x * scale;
                const ty = (containerHeight - bbox.height * scale) / 2 - bbox.y * scale;
                initialTransform = d3.zoomIdentity.translate(tx, ty).scale(scale);
            }
        }

        // Remove viewBox so we control sizing via transform
        svgNode.removeAttribute('viewBox');

        // Track drag to distinguish clicks from pans
        let startX, startY;
        svg.on('mousedown.dragtrack', (e) => {
            startX = e.clientX;
            startY = e.clientY;
            isDraggingRef.current = false;
            svg.style('cursor', 'grabbing');
        });
        svg.on('mousemove.dragtrack', (e) => {
            if (startX !== undefined) {
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
                    isDraggingRef.current = true;
                }
            }
        });
        svg.on('mouseup.dragtrack', () => {
            startX = undefined;
            startY = undefined;
            svg.style('cursor', 'grab');
        });

        const zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        svg.call(zoom);
        svg.call(zoom.transform, initialTransform);
    }, [svgContent, height]);

    const style = typeof height === 'string' ? { height } : { height: `${height}px` };

    return (
        <div
            className="svg-container"
            ref={containerRef}
            onClick={handleClick}
            style={style}
        />
    );
}

export default ZoomableSvg;
