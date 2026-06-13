import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { getDescendantsSvg, getDescendantsHierarchy } from "../services/api";
import { useSvgNavigation } from "../hooks/useSvgNavigation";
import ZoomableSvg from "./ZoomableSvg";

const THEMES = [
    { id: 'horizontal', label: 'Horizontal' },
    { id: 'vertical', label: 'Vertical' },
    { id: 'card', label: 'Card' },
];

function Tree() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [svgContent, setSvgContent] = useState(null)
    const [treeName, setTreeName] = useState(null)
    const [loading, setLoading] = useState(true)
    const [theme, setTheme] = useState('card')
    const handleSvgClick = useSvgNavigation()

    useEffect(() => {
        setLoading(true)
        setSvgContent(null)

        Promise.all([
            getDescendantsSvg(id, 10, theme),
            getDescendantsHierarchy(id, 10).catch(() => null)
        ])
            .then(([svg, hierarchy]) => {
                setSvgContent(svg)
                if (hierarchy) setTreeName(hierarchy.name)
                setLoading(false)
            })
            .catch(err => {
                console.error(err)
                setLoading(false)
            })
    }, [id, theme])

    const centeredStyle = {
        width: '100vw', height: '100vh',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#faf9f6'
    };

    if (loading) return <div style={centeredStyle}>Loading...</div>
    if (!svgContent) return <div style={centeredStyle}>No data found</div>

    return (
        <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: '#faf9f6' }}>
            <div style={{
                position: 'fixed', top: 16, left: 16, zIndex: 1000,
                display: 'flex', gap: 8, alignItems: 'center'
            }}>
                <button
                    onClick={() => navigate(`/person/${id}`)}
                    style={pillStyle}
                >
                    &larr; Back to {treeName || 'person'}
                </button>
                <div style={{ ...pillStyle, display: 'flex', gap: 0, padding: 0, overflow: 'hidden' }}>
                    {THEMES.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setTheme(t.id)}
                            style={{
                                padding: '8px 14px',
                                fontSize: '0.85rem',
                                border: 'none',
                                background: theme === t.id ? 'rgba(0,0,0,0.08)' : 'transparent',
                                fontWeight: theme === t.id ? 600 : 400,
                                color: '#333',
                                cursor: 'pointer',
                            }}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
            </div>
            <ZoomableSvg svgContent={svgContent} onClick={handleSvgClick} height="100vh" />
        </div>
    )
}

const pillStyle = {
    background: 'rgba(255, 255, 255, 0.85)',
    backdropFilter: 'blur(8px)',
    border: '1px solid rgba(0, 0, 0, 0.12)',
    borderRadius: 999,
    padding: '8px 16px',
    fontSize: '0.9rem',
    color: '#333',
    cursor: 'pointer',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
};

export default Tree;
