import { Link } from 'react-router-dom';
import './CensusSidebar.css';

function CensusSidebar({ censusRecords, personId, isOpen, onToggle }) {
    if (!isOpen) {
        return (
            <div className="census-tab" onClick={onToggle}>
                <span>Census ({censusRecords.length})</span>
            </div>
        );
    }

    return (
        <div className="census-sidebar">
            <div className="census-sidebar-header">
                <h3>Census Records</h3>
                <button className="census-close-btn" onClick={onToggle}>&times;</button>
            </div>
            <div className="census-sidebar-body">
                {censusRecords.map(record => (
                    <CensusRecord key={record.id} record={record} personId={personId} />
                ))}
            </div>
        </div>
    );
}

function CensusRecord({ record, personId }) {
    return (
        <div className="census-record">
            <div className="census-record-year">{record.year || '??'}</div>

            {record.address && (
                <div className="census-detail"><span className="census-label">Address</span><span>{record.address}</span></div>
            )}
            {record.occupation && (
                <div className="census-detail"><span className="census-label">Occupation</span><span>{record.occupation}</span></div>
            )}
            {record.status && (
                <div className="census-detail"><span className="census-label">Status</span><span>{record.status}</span></div>
            )}
            {record.birthPlace && (
                <div className="census-detail"><span className="census-label">Birthplace</span><span>{record.birthPlace}</span></div>
            )}
            {record.reference && (
                <div className="census-detail"><span className="census-label">Reference</span><span>{record.reference}</span></div>
            )}
            {record.url && (
                <div className="census-detail"><span className="census-label">Source</span><a href={record.url} target="_blank" rel="noopener noreferrer">View record</a></div>
            )}

            {record.household && record.household.length > 0 && (
                <table className="census-household-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Rel.</th>
                            <th>Age</th>
                            <th>Occupation</th>
                        </tr>
                    </thead>
                    <tbody>
                        {record.household.map(member => {
                            const isViewed = member.personId === personId;
                            return (
                                <tr key={member.personId ?? member.name} className={isViewed ? 'census-member-highlight' : ''}>
                                    <td>
                                        {member.personId && !isViewed ? (
                                            <Link to={`/person/${member.personId}`}>{member.name}</Link>
                                        ) : (
                                            <span className={isViewed ? 'census-member-self' : ''}>{member.name}</span>
                                        )}
                                    </td>
                                    <td>{member.relationship || ''}</td>
                                    <td>{member.age ?? ''}</td>
                                    <td>{member.occupation || ''}</td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            )}
        </div>
    );
}

export default CensusSidebar;
