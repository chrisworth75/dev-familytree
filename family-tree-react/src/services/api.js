import { API_BASE } from '../config';
import keycloak from '../keycloak';

// Refresh the token if it's near expiry, then attach it as a Bearer header.
// All /api/** calls go through this; static /images & /uploads are permitAll.
async function authFetch(url, opts = {}) {
    try {
        await keycloak.updateToken(30);
    } catch {
        keycloak.login();
    }
    const headers = { ...(opts.headers || {}) };
    if (keycloak.token) headers.Authorization = `Bearer ${keycloak.token}`;
    return fetch(url, { ...opts, headers });
}

export async function getStats() {
    const res = await authFetch(`${API_BASE}/api/stats`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
}

export async function getTopAncestors() {
    const res = await authFetch(`${API_BASE}/api/stats/top-ancestors`);
    if (!res.ok) throw new Error('Failed to fetch top ancestors');
    return res.json();
}

export async function getDescendantsHierarchy(personId, maxDepth = 10) {
    const res = await authFetch(`${API_BASE}/api/tree-data/person/${personId}/descendants?maxDepth=${maxDepth}`);
    if (!res.ok) throw new Error('Failed to fetch descendants hierarchy');
    return res.json();
}

export async function getDescendantsSvg(personId, maxDepth = 10, theme = 'vertical') {
    const res = await authFetch(`${API_BASE}/api/tree-svg/descendants/${personId}?maxDepth=${maxDepth}&theme=${theme}`);
    if (!res.ok) throw new Error('Failed to fetch descendants SVG');
    return res.text();
}

export async function getAncestorsHierarchy(personId, maxDepth = 10) {
    const res = await authFetch(`${API_BASE}/api/tree-data/person/${personId}/ancestors?maxDepth=${maxDepth}`);
    if (!res.ok) throw new Error('Failed to fetch ancestors hierarchy');
    return res.json();
}

export async function getMrcaPath(personA, personB) {
    const res = await authFetch(`${API_BASE}/api/tree-data/mrca?personA=${personA}&personB=${personB}`);
    if (!res.ok) throw new Error('Failed to fetch MRCA path');
    return res.json();
}

export async function getMatches(personId, limit, offset, hasAvatar = false) {
    let url = `${API_BASE}/api/match?person_id=${personId}&limit=${limit}&offset=${offset}`;
    if (hasAvatar) {
        url += '&hasAvatar=true';
    }
    const res = await authFetch(url);
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
    const res = await authFetch(`${API_BASE}/api/person/${personId}/summary`);
    if (!res.ok) return null;
    return res.json();
}

export async function getMatchLinkStatus(dnaTestId) {
    const res = await authFetch(`${API_BASE}/api/dna-tester/${dnaTestId}/link-status`);
    if (!res.ok) return null;
    return res.json();
}

export async function getCensusRecords(personId) {
    const res = await authFetch(`${API_BASE}/api/person/${personId}/census`);
    if (!res.ok) return [];
    return res.json();
}

export async function fetchSvgText(url) {
    const res = await authFetch(url);
    if (!res.ok) return null;
    return res.text();
}

export async function getPhotos() {
    const res = await authFetch(`${API_BASE}/api/photos`);
    if (!res.ok) throw new Error('Failed to fetch photos');
    return res.json();
}

export async function getPhotoDetail(id) {
    const res = await authFetch(`${API_BASE}/api/photos/${id}`);
    if (!res.ok) throw new Error('Failed to fetch photo detail');
    return res.json();
}

export async function uploadPhoto(formData) {
    const res = await authFetch(`${API_BASE}/api/photos`, {
        method: 'POST',
        body: formData
    });
    if (!res.ok) throw new Error('Failed to upload photo');
    return res.json();
}

export async function deletePhoto(id) {
    const res = await authFetch(`${API_BASE}/api/photos/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete photo');
}

export async function addPhotoTag(photoId, personId) {
    const res = await authFetch(`${API_BASE}/api/photos/${photoId}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ personId })
    });
    if (!res.ok) throw new Error('Failed to add tag');
    return res.json();
}

export async function removePhotoTag(photoId, personId) {
    const res = await authFetch(`${API_BASE}/api/photos/${photoId}/tags/${personId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to remove tag');
}

export async function getPersonPhotos(personId) {
    const res = await authFetch(`${API_BASE}/api/person/${personId}/photos`);
    if (!res.ok) return [];
    return res.json();
}

export async function searchPersons(name, { familyOnly = true } = {}) {
    const res = await authFetch(`${API_BASE}/api/person/search?name=${encodeURIComponent(name)}&familyOnly=${familyOnly}&limit=10`);
    if (!res.ok) return [];
    return res.json();
}
