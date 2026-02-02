import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = 'http://localhost:3200';
const MY_PERSON_ID = '1000';
const PAGE_SIZE = 50;

function DNA() {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const observerRef = useRef();

    const loadMatches = useCallback(async (offset = 0) => {
        const isInitial = offset === 0;
        if (isInitial) setLoading(true);
        else setLoadingMore(true);

        try {
            const res = await fetch(
                `${API_BASE}/api/match?person_id=${MY_PERSON_ID}&limit=${PAGE_SIZE}&offset=${offset}`
            );
            const data = await res.json();

            if (isInitial) {
                setMatches(data);
            } else {
                setMatches(prev => [...prev, ...data]);
            }

            setHasMore(data.length === PAGE_SIZE);
        } catch (err) {
            console.error('Failed to fetch matches:', err);
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    }, []);

    useEffect(() => {
        loadMatches(0);
    }, [loadMatches]);

    // Intersection Observer for infinite scroll
    const lastRowRef = useCallback(node => {
        if (loadingMore) return;
        if (observerRef.current) observerRef.current.disconnect();

        observerRef.current = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && hasMore) {
                loadMatches(matches.length);
            }
        });

        if (node) observerRef.current.observe(node);
    }, [loadingMore, hasMore, matches.length, loadMatches]);

    if (loading) return <div className="page">Loading...</div>;

    return (
        <div className="page">
            <h1>DNA Matches</h1>
            <p>{matches.length} matches loaded</p>

            <table>
                <thead>
                <tr>
                    <th>Name</th>
                    <th>Shared cM</th>
                    <th>Relationship</th>
                    <th>Side</th>
                </tr>
                </thead>
                <tbody>
                {matches.map((match, index) => (
                    <tr
                        key={match.dnaTestId}
                        ref={index === matches.length - 1 ? lastRowRef : null}
                    >
                        <td>{match.name}</td>
                        <td>{match.sharedCm}</td>
                        <td>{match.predictedRelationship || '-'}</td>
                        <td>{match.matchSide || '-'}</td>
                    </tr>
                ))}
                </tbody>
            </table>

            {loadingMore && <p>Loading more...</p>}
            {!hasMore && <p>That's all of them!</p>}
        </div>
    );
}

export default DNA;
