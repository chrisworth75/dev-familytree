import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE } from '../config';
import {
    getPhotos, getPhotoDetail, uploadPhoto, deletePhoto,
    addPhotoTag, removePhotoTag, searchPersons
} from '../services/api';
import './Photos.css';

function PhotoModal({ photo, photos, onClose, onNavigate, onDelete, onTagsChanged }) {
    const [detail, setDetail] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const debounceRef = useRef(null);

    const loadDetail = useCallback((id) => {
        getPhotoDetail(id).then(setDetail).catch(() => {});
    }, []);

    useEffect(() => {
        if (photo) loadDetail(photo.id);
    }, [photo, loadDetail]);

    useEffect(() => {
        const handleKey = (e) => {
            if (e.key === 'Escape') onClose();
            if (e.key === 'ArrowLeft') onNavigate(-1);
            if (e.key === 'ArrowRight') onNavigate(1);
        };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [onClose, onNavigate]);

    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        if (searchQuery.length < 2) {
            setSearchResults([]);
            return;
        }
        debounceRef.current = setTimeout(() => {
            searchPersons(searchQuery).then(setSearchResults);
        }, 300);
        return () => clearTimeout(debounceRef.current);
    }, [searchQuery]);

    if (!photo) return null;

    const handleBackdropClick = (e) => {
        if (e.target === e.currentTarget) onClose();
    };

    const handleDelete = async () => {
        if (!window.confirm('Delete this photo?')) return;
        await deletePhoto(photo.id);
        onDelete(photo.id);
    };

    const handleAddTag = async (personId) => {
        await addPhotoTag(photo.id, personId);
        setSearchQuery('');
        setSearchResults([]);
        loadDetail(photo.id);
        onTagsChanged();
    };

    const handleRemoveTag = async (personId) => {
        await removePhotoTag(photo.id, personId);
        loadDetail(photo.id);
        onTagsChanged();
    };

    const tags = detail?.tags || [];
    const taggedIds = new Set(tags.map(t => t.personId));

    return (
        <div className="photo-modal-overlay" onClick={handleBackdropClick}>
            {photos.length > 1 && (
                <>
                    <button className="photo-nav-btn prev" onClick={() => onNavigate(-1)}>&lsaquo;</button>
                    <button className="photo-nav-btn next" onClick={() => onNavigate(1)}>&rsaquo;</button>
                </>
            )}
            <div className="photo-modal">
                <button className="photo-modal-close" onClick={onClose}>&times;</button>
                <img
                    className="photo-modal-image"
                    src={`${API_BASE}/api/photos/images/${photo.id}/original`}
                    alt={photo.description || 'Photo'}
                />

                <div className="photo-modal-meta">
                    <span className="photo-card-desc">{photo.description || 'No description'}</span>
                    {photo.yearTaken && <span className="photo-card-year">{photo.yearTaken}</span>}
                    <button className="photo-modal-delete" onClick={handleDelete}>Delete</button>
                </div>

                <div className="photo-tags-section">
                    <h3>Tagged People</h3>
                    <div className="photo-tag-list">
                        {tags.map(tag => (
                            <span key={tag.personId} className="photo-tag-pill">
                                <Link to={`/person/${tag.personId}`}>{tag.personName}</Link>
                                <button className="photo-tag-remove" onClick={() => handleRemoveTag(tag.personId)}>&times;</button>
                            </span>
                        ))}
                        {tags.length === 0 && <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>No one tagged yet</span>}
                    </div>

                    <div className="photo-tag-search">
                        <input
                            type="text"
                            placeholder="Search to tag a person..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        {searchResults.length > 0 && (
                            <div className="photo-search-results">
                                {searchResults
                                    .filter(p => !taggedIds.has(p.id))
                                    .map(p => (
                                        <div key={p.id} onClick={() => handleAddTag(p.id)}>
                                            {p.firstName} {p.surname}
                                            {p.birthYearApprox && <span style={{ color: 'var(--color-text-muted)', marginLeft: '0.5rem' }}>b. {p.birthYearApprox}</span>}
                                        </div>
                                    ))
                                }
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

function Photos() {
    const [photos, setPhotos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedIndex, setSelectedIndex] = useState(null);

    // Upload state
    const [description, setDescription] = useState('');
    const [yearTaken, setYearTaken] = useState('');
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState('');
    const fileInputRef = useRef(null);

    useEffect(() => {
        getPhotos().then(p => {
            setPhotos(p);
            setLoading(false);
        }).catch(() => setLoading(false));
    }, []);

    const handleUpload = async () => {
        const file = fileInputRef.current?.files[0];
        if (!file) return;

        setUploading(true);
        setUploadError('');

        const formData = new FormData();
        formData.append('file', file);
        if (description) formData.append('description', description);
        if (yearTaken) formData.append('yearTaken', yearTaken);

        try {
            const newPhoto = await uploadPhoto(formData);
            setPhotos(prev => [newPhoto, ...prev]);
            setDescription('');
            setYearTaken('');
            fileInputRef.current.value = '';
        } catch (err) {
            setUploadError(err.message);
        } finally {
            setUploading(false);
        }
    };

    const handleNavigate = useCallback((direction) => {
        setSelectedIndex(prev => {
            if (prev === null) return null;
            const next = prev + direction;
            if (next < 0) return photos.length - 1;
            if (next >= photos.length) return 0;
            return next;
        });
    }, [photos.length]);

    const handleClose = useCallback(() => {
        setSelectedIndex(null);
    }, []);

    const handleDelete = (photoId) => {
        setPhotos(prev => prev.filter(p => p.id !== photoId));
        setSelectedIndex(null);
    };

    const handleTagsChanged = () => {
        // Refresh the list to update tag counts
        getPhotos().then(setPhotos).catch(() => {});
    };

    if (loading) return <div className="page">Loading...</div>;

    return (
        <div className="page">
            <h1>Photos</h1>

            <div className="photo-upload">
                <label>
                    File
                    <input type="file" ref={fileInputRef} accept="image/jpeg,image/png" />
                </label>
                <label>
                    Description
                    <input type="text" value={description} onChange={e => setDescription(e.target.value)} />
                </label>
                <label>
                    Year
                    <input type="number" value={yearTaken} onChange={e => setYearTaken(e.target.value)} />
                </label>
                <button onClick={handleUpload} disabled={uploading}>
                    {uploading ? 'Uploading...' : 'Upload'}
                </button>
                {uploadError && <div className="photo-upload-error">{uploadError}</div>}
            </div>

            <div className="photo-grid">
                {photos.map((photo, idx) => (
                    <div key={photo.id} className="photo-card" onClick={() => setSelectedIndex(idx)}>
                        <img
                            src={`${API_BASE}/api/photos/images/${photo.id}/thumb`}
                            alt={photo.description || 'Photo'}
                            loading="lazy"
                        />
                        <div className="photo-card-info">
                            <span className="photo-card-desc">{photo.description || ''}</span>
                            {photo.yearTaken && <span className="photo-card-year">{photo.yearTaken}</span>}
                            {photo.tagCount > 0 && <span className="photo-card-tags">{photo.tagCount}</span>}
                        </div>
                    </div>
                ))}
            </div>

            {selectedIndex !== null && (
                <PhotoModal
                    photo={photos[selectedIndex]}
                    photos={photos}
                    onClose={handleClose}
                    onNavigate={handleNavigate}
                    onDelete={handleDelete}
                    onTagsChanged={handleTagsChanged}
                />
            )}
        </div>
    );
}

export default Photos;
