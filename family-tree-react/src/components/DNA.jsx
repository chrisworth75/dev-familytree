import { useState, useEffect, useRef, useCallback } from 'react';
import MatchCard from './MatchCard';
import { MY_PERSON_ID } from '../config';
import { getMatches } from '../services/api';

const PAGE_SIZE = 50;

function DNA() {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const [avatarOnly, setAvatarOnly] = useState(false);
    const observerRef = useRef();

    const loadMatches = useCallback(async (offset = 0, filterAvatarOnly = false) => {
        const isInitial = offset === 0;
        if (isInitial) setLoading(true);
        else setLoadingMore(true);

        try {
            const data = await getMatches(MY_PERSON_ID, PAGE_SIZE, offset, filterAvatarOnly);

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
        loadMatches(0, avatarOnly);
    }, [loadMatches, avatarOnly]);

    const handleAvatarFilterChange = (e) => {
        const checked = e.target.checked;
        setAvatarOnly(checked);
        setMatches([]);
        setHasMore(true);
    };

    const lastRowRef = useCallback(node => {
        if (loadingMore) return;
        if (observerRef.current) observerRef.current.disconnect();

        observerRef.current = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && hasMore) {
                loadMatches(matches.length, avatarOnly);
            }
        });

        if (node) observerRef.current.observe(node);
    }, [loadingMore, hasMore, matches.length, loadMatches, avatarOnly]);

    if (loading) return <div className="page">Loading...</div>;

    return (
        <div className="page">
            <h1>DNA Matches</h1>
            <p>{matches.length} matches loaded</p>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <input
                    type="checkbox"
                    checked={avatarOnly}
                    onChange={handleAvatarFilterChange}
                />
                Show only matches with photos
            </label>

            <div className="match-list">
                {matches.map((match, index) => (
                    <div
                        key={match.dnaTestId}
                        ref={index === matches.length - 1 ? lastRowRef : null}
                    >
                        <MatchCard match={match} />
                    </div>
                ))}
            </div>

            {loadingMore && <p>Loading more...</p>}
            {!hasMore && <p>That's all of them!</p>}
        </div>
    );
}

export default DNA;
