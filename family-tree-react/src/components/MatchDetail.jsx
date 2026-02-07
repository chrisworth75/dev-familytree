// MatchDetail.jsx
import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './MatchDetail.css';
import { API_BASE, MY_PERSON_ID } from '../config';
import { getMatchLinkStatus } from '../services/api';

function MatchDetail() {
    const { dnaTestId } = useParams();
    const navigate = useNavigate();
    const [match, setMatch] = useState(null);
    const [loading, setLoading] = useState(true);
    const [mrcaError, setMrcaError] = useState(false);
    const fileInputRef = useRef();

    useEffect(() => {
        getMatchLinkStatus(dnaTestId).then(data => {
            if (data?.personId) {
                navigate(`/person/${data.personId}`, { replace: true });
            }
        });
    }, [dnaTestId, navigate]);

    useEffect(() => {
        fetch(`${API_BASE}/api/match/${dnaTestId}`)
            .then(res => {
                if (!res.ok) return null;
                return res.json();
            })
            .then(data => {
                setMatch(data);
                setLoading(false);
            })
            .catch(() => {
                setMatch(null);
                setLoading(false);
            });
    }, [dnaTestId]);

    useEffect(() => {
        setMrcaError(false);
    }, [match?.personId]);

    const handleAvatarClick = () => {
        fileInputRef.current.click();
    };

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('avatar', file);

        const res = await fetch(`${API_BASE}/api/match/${dnaTestId}/avatar`, {
            method: 'POST',
            body: formData
        });

        if (res.ok) {
            const updated = await res.json();
            setMatch(updated);
        }
    };

    if (loading) return <div className="page">Loading...</div>;
    if (!match) return <div className="page">Match not found</div>;

    const mrcaUrl = match.personId
        ? `${API_BASE}/api/tree-svg/mrca?personA=${MY_PERSON_ID}&personB=${match.personId}`
        : null;

    return (
        <div className="page match-detail">
            <div className="match-detail-header">
                <div
                    className="match-detail-avatar"
                    onClick={handleAvatarClick}
                    style={{ cursor: 'pointer' }}
                >
                    {match.avatarPath ? (
                        <img src={`${API_BASE}/uploads/${match.avatarPath}`} alt={match.name} />
                    ) : (
                        <div className="avatar-placeholder">
                            <span>Click to upload</span>
                        </div>
                    )}
                </div>

                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept="image/*"
                    style={{ display: 'none' }}
                />

                <h1>{match.name}</h1>
            </div>

            <div style={{ marginTop: '2rem' }}>
                <h2>Common Ancestor Path</h2>
                {mrcaUrl ? (
                    mrcaError ? (
                        <p style={{ color: '#666' }}>No common ancestor found yet</p>
                    ) : (
                        <img
                            src={mrcaUrl}
                            alt="MRCA tree"
                            onError={() => setMrcaError(true)}
                            style={{ maxWidth: '100%', marginTop: '1rem' }}
                        />
                    )
                ) : (
                    <p style={{ color: '#888', fontStyle: 'italic' }}>
                        Link this match to a person in the tree to see the ancestor path
                    </p>
                )}
            </div>
        </div>
    );
}

export default MatchDetail;
