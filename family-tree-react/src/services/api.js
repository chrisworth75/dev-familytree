import { API_BASE } from '../config';

export async function getStats() {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
}

export async function getTopAncestors() {
    const res = await fetch(`${API_BASE}/api/stats/top-ancestors`);
    if (!res.ok) throw new Error('Failed to fetch top ancestors');
    return res.json();
}

export async function getDescendantsHierarchy(personId, maxDepth = 10) {
    const res = await fetch(`${API_BASE}/api/tree-data/person/${personId}/descendants?maxDepth=${maxDepth}`);
    if (!res.ok) throw new Error('Failed to fetch descendants hierarchy');
    return res.json();
}

export async function getDescendantsSvg(personId, maxDepth = 10) {
    const res = await fetch(`${API_BASE}/api/tree-svg/descendants/${personId}?maxDepth=${maxDepth}`);
    if (!res.ok) throw new Error('Failed to fetch descendants SVG');
    return res.text();
}

export async function getAncestorsHierarchy(personId, maxDepth = 10) {
    const res = await fetch(`${API_BASE}/api/tree-data/person/${personId}/ancestors?maxDepth=${maxDepth}`);
    if (!res.ok) throw new Error('Failed to fetch ancestors hierarchy');
    return res.json();
}

export async function getMrcaPath(personA, personB) {
    const res = await fetch(`${API_BASE}/api/tree-data/mrca?personA=${personA}&personB=${personB}`);
    if (!res.ok) throw new Error('Failed to fetch MRCA path');
    return res.json();
}

export async function getMatches(personId, limit, offset, hasAvatar = false) {
    let url = `${API_BASE}/api/match?person_id=${personId}&limit=${limit}&offset=${offset}`;
    if (hasAvatar) {
        url += '&hasAvatar=true';
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch matches');
    return res.json();
}

export function getPersonImageUrl(personId) {
    return `${API_BASE}/images/${personId}.png`;
}

export function getAvatarUrl(avatarPath) {
    return `/uploads/${avatarPath}`;
}

export async function getPersonSummary(personId) {
    const res = await fetch(`${API_BASE}/api/person/${personId}/summary`);
    if (!res.ok) return null;
    return res.json();
}

export async function getMatchLinkStatus(dnaTestId) {
    const res = await fetch(`${API_BASE}/api/dna-tester/${dnaTestId}/link-status`);
    if (!res.ok) return null;
    return res.json();
}

export async function getCensusRecords(personId) {
    const res = await fetch(`${API_BASE}/api/person/${personId}/census`);
    if (!res.ok) return [];
    return res.json();
}

export async function fetchSvgText(url) {
    const res = await fetch(url);
    if (!res.ok) return null;
    return res.text();
}
