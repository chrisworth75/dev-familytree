// MatchDetail.jsx
import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import './MatchDetail.css';

const API_BASE = 'http://localhost:3200';

function MatchDetail() {
    const { dnaTestId } = useParams();
    const [match, setMatch] = useState(null);
    const [loading, setLoading] = useState(true);
    const fileInputRef = useRef();

    useEffect(() => {
        fetch(`${API_BASE}/api/match/${dnaTestId}`)
            .then(res => res.json())
            .then(data => {
                setMatch(data);
                setLoading(false);
            });
    }, [dnaTestId]);

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

    return (
        <div className="page match-detail">
            <div className="match-detail-header">
                <div
                    className="match-detail-avatar"
                    onClick={handleAvatarClick}
                    style={{ cursor: 'pointer' }}
                >
                    {match.avatarPath ? (
                        <img src={`/uploads/${match.avatarPath}`} alt={match.name} />
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
        </div>
    );
}

export default MatchDetail;
