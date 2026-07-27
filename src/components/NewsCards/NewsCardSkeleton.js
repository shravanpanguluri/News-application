import React from 'react';
import './NewsCardSkeleton.css';

const NewsCardSkeleton = () => (
    <div className="skeleton-card">
        <div className="skeleton-image shimmer" />
        <div className="skeleton-content">
            <div className="skeleton-line skeleton-title shimmer" />
            <div className="skeleton-line skeleton-title-short shimmer" />
            <div className="skeleton-line skeleton-desc shimmer" />
            <div className="skeleton-line skeleton-desc-short shimmer" />
            <div className="skeleton-meta">
                <div className="skeleton-line skeleton-source shimmer" />
                <div className="skeleton-line skeleton-date shimmer" />
            </div>
        </div>
    </div>
);

export default NewsCardSkeleton;
