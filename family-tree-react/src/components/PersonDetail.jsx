import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getPersonSummary, getAvatarUrl, fetchSvgText } from '../services/api';
import { API_BASE, MY_PERSON_ID } from '../config';
import './PersonDetail.css';

function PersonDetail() {
    const { id } = useParams();
    const personId = Number(id);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    const [ancestorSvg, setAncestorSvg] = useState(null);
    const [descendantSvg, setDescendantSvg] = useState(null);
    const [mrcaSvg, setMrcaSvg] = useState(null);
    const [svgLoading, setSvgLoading] = useState({ ancestors: true, descendants: true, mrca: true });

    const [ancestorsOpen, setAncestorsOpen] = useState(true);
    const [descendantsOpen, setDescendantsOpen] = useState(true);
    const [mrcaOpen, setMrcaOpen] = useState(true);

    useEffect(() => {
        setLoading(true);
        setData(null);
        setAncestorSvg(null);
        setDescendantSvg(null);
        setMrcaSvg(null);
        setSvgLoading({ ancestors: true, descendants: true, mrca: true });

        getPersonSummary(personId).then(d => {
            setData(d);
            setLoading(false);

            if (!d) return;

            fetchSvgText(`${API_BASE}/api/tree-svg/ancestors/${personId}?maxDepth=3`)
                .then(svg => { setAncestorSvg(svg); setSvgLoading(prev => ({ ...prev, ancestors: false })); })
                .catch(() => setSvgLoading(prev => ({ ...prev, ancestors: false })));

            fetchSvgText(`${API_BASE}/api/tree-svg/descendants/${personId}?maxDepth=3`)
                .then(svg => { setDescendantSvg(svg); setSvgLoading(prev => ({ ...prev, descendants: false })); })
                .catch(() => setSvgLoading(prev => ({ ...prev, descendants: false })));

            if (d.match && personId !== MY_PERSON_ID) {
                fetchSvgText(`${API_BASE}/api/tree-svg/mrca?personA=${MY_PERSON_ID}&personB=${personId}`)
                    .then(svg => { setMrcaSvg(svg); setSvgLoading(prev => ({ ...prev, mrca: false })); })
                    .catch(() => setSvgLoading(prev => ({ ...prev, mrca: false })));
            } else {
                setSvgLoading(prev => ({ ...prev, mrca: false }));
            }
        });
    }, [personId]);

    if (loading) return <div className="page">Loading...</div>;
    if (!data) return <div className="page">Person not found</div>;

    const { person, father, mother, spouses, children, siblings, match } = data;

    const avatarPath = person.avatarPath || (match && match.avatarPath);
    const genderClass = person.gender === 'M' ? 'male' : person.gender === 'F' ? 'female' : 'unknown';
    const genderIcon = person.gender === 'M' ? '\u2642' : person.gender === 'F' ? '\u2640' : '?';

    const lifespanParts = [];
    const birthYear = person.birthDate ? new Date(person.birthDate).getFullYear() : person.birthYearApprox;
    const deathYear = person.deathDate ? new Date(person.deathDate).getFullYear() : person.deathYearApprox;
    if (birthYear) {
        let part = `b. ${birthYear}`;
        if (person.birthPlace) part += `, ${person.birthPlace}`;
        lifespanParts.push(part);
    }
    if (deathYear) {
        let part = `d. ${deathYear}`;
        if (person.deathPlace) part += `, ${person.deathPlace}`;
        lifespanParts.push(part);
    }

    const matchNameDiffers = match && match.name &&
        match.name !== `${person.firstName || ''} ${person.surname || ''}`.trim();

    return (
        <div className="page person-detail">
            <div className="person-header">
                <div className="person-avatar">
                    {avatarPath ? (
                        <img src={getAvatarUrl(avatarPath)} alt={person.firstName} />
                    ) : (
                        <div className={`person-avatar-placeholder ${genderClass}`}>
                            {genderIcon}
                        </div>
                    )}
                </div>
                <h1>{person.firstName}{person.surname ? ` ${person.surname}` : ''}</h1>
                {matchNameDiffers && (
                    <div className="person-subtitle">"{match.name}" on Ancestry</div>
                )}
                {lifespanParts.length > 0 && (
                    <div className="person-lifespan">{lifespanParts.join(' \u2014 ')}</div>
                )}
                {match && (
                    <div className="person-badge">
                        {match.predictedRelationship}{match.sharedCm ? ` \u00b7 ${match.sharedCm} cM` : ''}
                    </div>
                )}
            </div>

            <div className="person-family">
                <h2>Family</h2>

                {(father || mother) && (
                    <div className="family-subsection">
                        <h3>Parents</h3>
                        <div className="family-links">
                            {father && <PersonLink person={father} label="Father" />}
                            {mother && <PersonLink person={mother} label="Mother" />}
                        </div>
                    </div>
                )}

                {spouses && spouses.length > 0 && (
                    <div className="family-subsection">
                        <h3>{spouses.length === 1 ? 'Spouse' : 'Spouses'}</h3>
                        <div className="family-links">
                            {spouses.map(s => <PersonLink key={s.id} person={s} />)}
                        </div>
                    </div>
                )}

                {children && children.length > 0 && (
                    <div className="family-subsection">
                        <h3>Children</h3>
                        <div className="family-links">
                            {children.map(c => <PersonLink key={c.id} person={c} />)}
                        </div>
                    </div>
                )}

                {siblings && siblings.length > 0 && (
                    <div className="family-subsection">
                        <h3>Siblings</h3>
                        <div className="family-links">
                            {siblings.map(s => <PersonLink key={s.id} person={s} />)}
                        </div>
                    </div>
                )}
            </div>

            {(ancestorSvg || svgLoading.ancestors) && (
                <div className="svg-section">
                    <h2 onClick={() => setAncestorsOpen(!ancestorsOpen)}>
                        {ancestorsOpen ? '\u25BC' : '\u25B6'} Ancestors
                    </h2>
                    {ancestorsOpen && (
                        svgLoading.ancestors
                            ? <div className="svg-loading">Loading ancestor tree...</div>
                            : ancestorSvg && <div className="svg-container" dangerouslySetInnerHTML={{ __html: ancestorSvg }} />
                    )}
                </div>
            )}

            {(descendantSvg || svgLoading.descendants) && (
                <div className="svg-section">
                    <h2 onClick={() => setDescendantsOpen(!descendantsOpen)}>
                        {descendantsOpen ? '\u25BC' : '\u25B6'} Descendants
                    </h2>
                    {descendantsOpen && (
                        svgLoading.descendants
                            ? <div className="svg-loading">Loading descendant tree...</div>
                            : descendantSvg && <div className="svg-container" dangerouslySetInnerHTML={{ __html: descendantSvg }} />
                    )}
                </div>
            )}

            {(mrcaSvg || (match && personId !== MY_PERSON_ID && svgLoading.mrca)) && (
                <div className="svg-section">
                    <h2 onClick={() => setMrcaOpen(!mrcaOpen)}>
                        {mrcaOpen ? '\u25BC' : '\u25B6'} Common Ancestor Path
                    </h2>
                    {mrcaOpen && (
                        svgLoading.mrca
                            ? <div className="svg-loading">Loading MRCA tree...</div>
                            : mrcaSvg && <div className="svg-container" dangerouslySetInnerHTML={{ __html: mrcaSvg }} />
                    )}
                </div>
            )}
        </div>
    );
}

function PersonLink({ person, label }) {
    const name = `${person.firstName || ''} ${person.surname || ''}`.trim() || 'Unknown';
    const birthYear = person.birthDate ? new Date(person.birthDate).getFullYear() : person.birthYearApprox;

    return (
        <Link to={`/person/${person.id}`} className="family-link">
            {label && <span>{label}:</span>}
            <span>{name}</span>
            {birthYear && <span className="family-link-year">b. {birthYear}</span>}
        </Link>
    );
}

export default PersonDetail;
