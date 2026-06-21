import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getStats, getTopAncestors, getTopByCensus, getAvatarUrl } from "../services/api";

function Home() {
    const [stats, setStats] = useState(null)
    const [topAncestors, setTopAncestors] = useState([])
    const [topByCensus, setTopByCensus] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        Promise.all([getStats(), getTopAncestors(), getTopByCensus()])
            .then(([statsData, ancestorsData, censusData]) => {
                setStats(statsData)
                setTopAncestors(Array.isArray(ancestorsData) ? ancestorsData : [])
                setTopByCensus(Array.isArray(censusData) ? censusData : [])
                setLoading(false)
            })
            .catch(err => {
                console.error('Failed to fetch:', err)
                setLoading(false)
            })
    }, [])

    if (loading) return <div className="page">Loading...</div>
    if (!stats) return <div className="page">Failed to load stats</div>

    return (
        <div className="page">
            <h1>Dashboard</h1>
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-value">{stats.treeSize.toLocaleString()}</div>
                    <div className="stat-label">People in Tree</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{stats.dnaMatchCount.toLocaleString()}</div>
                    <div className="stat-label">DNA Matches</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{stats.linkedMatches}</div>
                    <div className="stat-label">Identified</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{stats.unlinkedMatches.toLocaleString()}</div>
                    <div className="stat-label">Unidentified</div>
                </div>
            </div>

            <h2 style={{marginTop: '2rem'}}>Top Ancestors by Descendants</h2>
            <div className="ancestors-list">
                {topAncestors.map((ancestor, index) => (
                    <Link to={'/person/' + ancestor.id} key={ancestor.id} className="ancestor-card">
                        <span className="ancestor-rank">#{index + 1}</span>
                        {ancestor.avatarPath ? (
                            <img
                                src={getAvatarUrl(ancestor.avatarPath)}
                                alt=""
                                className="ancestor-photo"
                            />
                        ) : (
                            <div className="ancestor-photo ancestor-photo-placeholder" />
                        )}
                        <span className="ancestor-name">{ancestor.name}</span>
                        {ancestor.birthYear && <span className="ancestor-year">b. {ancestor.birthYear}</span>}
                        <span className="ancestor-count">{ancestor.descendantCount} descendants</span>
                    </Link>
                ))}
            </div>

            <h2 style={{marginTop: '2rem'}}>Top Ancestors by Census Records</h2>
            <div className="ancestors-list">
                {topByCensus.map((ancestor, index) => (
                    <Link to={'/person/' + ancestor.id} key={ancestor.id} className="ancestor-card">
                        <span className="ancestor-rank">#{index + 1}</span>
                        {ancestor.avatarPath ? (
                            <img
                                src={getAvatarUrl(ancestor.avatarPath)}
                                alt=""
                                className="ancestor-photo"
                            />
                        ) : (
                            <div className="ancestor-photo ancestor-photo-placeholder" />
                        )}
                        <span className="ancestor-name">{ancestor.name}</span>
                        {ancestor.birthYear && <span className="ancestor-year">b. {ancestor.birthYear}</span>}
                        <span className="ancestor-count">{ancestor.censusCount} census records</span>
                    </Link>
                ))}
            </div>
        </div>
    )
}

export default Home
