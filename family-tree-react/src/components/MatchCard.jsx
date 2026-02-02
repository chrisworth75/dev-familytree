import { Link } from 'react-router-dom';
import './MatchCard.css'

import gen1 from '../assets/gen-1.svg';
import gen2 from '../assets/gen-2.svg';
import gen3 from '../assets/gen-3.svg';
import gen4 from '../assets/gen-4.svg';
import gen5 from '../assets/gen-5.svg';
import gen6 from '../assets/gen-6.svg';
import gen7 from '../assets/gen-7.svg';
import gen8 from '../assets/gen-8.svg';

const genIcons = [null, gen1, gen2, gen3, gen4, gen5, gen6, gen7, gen8];

function SharedCmIndicator({ cm }) {
    const thresholds = [20, 50, 100, 200, 400, 850, 1700];

    let filled = 1;
    for (const threshold of thresholds) {
        if (cm >= threshold) filled++;
    }

    return (
        <div className="indicator">
            <svg width="64" height="12">
                {[...Array(8)].map((_, i) => (
                    <rect
                        key={i}
                        x={i * 8}
                        y={0}
                        width="6"
                        height="12"
                        rx="1"
                        fill={i < filled ? '#2563eb' : '#e5e7eb'}
                    />
                ))}
            </svg>
            <span className="indicator-label">{cm} cM</span>
        </div>
    );
}

function GenerationDepth({ generations }) {
    if (!generations) return null;

    const gens = Math.min(Math.max(generations, 1), 8);
    const icon = genIcons[gens];

    return (
        <div className="indicator">
            <img src={icon} alt={`${generations} generations`} height="14" />
            <span className="indicator-label">{generations} gen</span>
        </div>
    );
}

function Avatar({ name, avatarPath }) {
    if (avatarPath) {
        return <img src={`/uploads/${avatarPath}`} alt={name} className="avatar" />;
    }

    // Initials fallback
    const initials = name
        .split(' ')
        .map(n => n[0])
        .join('')
        .slice(0, 2)
        .toUpperCase();

    return <div className="avatar avatar-initials">{initials}</div>;
}

function formatSide(side) {
    if (side === 'paternal') return "Dad's side";
    if (side === 'maternal') return "Mum's side";
    if (side === 'both') return 'Both sides';
    return null;
}

function MatchCard({ match }) {
    const side = formatSide(match.matchSide);

    return (
        <Link to={`/dna/match/${match.dnaTestId}`} className="match-card">
            <Avatar name={match.name} avatarPath={match.avatarPath} />

            <div className="match-info">
                <span className="match-name">{match.name}</span>
                {side && <span className="match-side">{side}</span>}
            </div>

            <div className="match-indicators">
                <GenerationDepth generations={match.generationDepth} />
                <SharedCmIndicator cm={match.sharedCm} />
            </div>
        </Link>
    );
}

export default MatchCard;
