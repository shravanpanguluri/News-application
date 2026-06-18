import React, { useState, useEffect, useRef } from 'react';
import { Segment, Header, Icon, Button, Label, Transition } from 'semantic-ui-react';
import './GovShorts.css';

const SWIPE_THRESHOLD = 75;   // px drag needed to commit a swipe
const SWIPE_MODE_W    = 1004; // width breakpoint
const SWIPE_MODE_H    = 725;  // height breakpoint

const GovShorts = ({ articles = [], onArticleClick }) => {
    const [currentIndex, setCurrentIndex]     = useState(0);
    const [direction, setDirection]           = useState('up');
    const [visible, setTransitionVisible]     = useState(true);
    const [isSwipeMode, setIsSwipeMode]       = useState(
        () => window.innerWidth < SWIPE_MODE_W || window.innerHeight < SWIPE_MODE_H
    );
    const [dragX, setDragX]                   = useState(0);
    const [isDragging, setIsDragging]         = useState(false);
    const [showHint, setShowHint]             = useState(true);
    const dragStartX                          = useRef(0);
    const hintTimer                           = useRef(null);

    // Watch viewport — switch modes on resize
    useEffect(() => {
        const check = () =>
            setIsSwipeMode(window.innerWidth < SWIPE_MODE_W || window.innerHeight < SWIPE_MODE_H);
        window.addEventListener('resize', check);
        return () => window.removeEventListener('resize', check);
    }, []);

    // Auto-hide swipe hint after 3 s
    useEffect(() => {
        if (isSwipeMode) {
            setShowHint(true);
            hintTimer.current = setTimeout(() => setShowHint(false), 3000);
        }
        return () => clearTimeout(hintTimer.current);
    }, [isSwipeMode]);

    /* ── Navigation ──────────────────────────────── */
    const nextShort = () => {
        if (currentIndex < articles.length - 1) {
            setTransitionVisible(false);
            setTimeout(() => {
                setDirection('up');
                setCurrentIndex(p => p + 1);
                setTransitionVisible(true);
            }, 250);
        }
    };

    const prevShort = () => {
        if (currentIndex > 0) {
            setTransitionVisible(false);
            setTimeout(() => {
                setDirection('down');
                setCurrentIndex(p => p - 1);
                setTransitionVisible(true);
            }, 250);
        }
    };

    /* ── Drag / Swipe handlers ───────────────────── */
    const startDrag = (clientX) => {
        dragStartX.current = clientX;
        setIsDragging(true);
        setShowHint(false);
    };

    const moveDrag = (clientX) => {
        if (!isDragging) return;
        setDragX(clientX - dragStartX.current);
    };

    const endDrag = () => {
        if (!isDragging) return;
        setIsDragging(false);
        const dx = dragX;
        setDragX(0); // spring back visually first
        if (dx < -SWIPE_THRESHOLD)      nextShort(); // ← swipe left = NEXT
        else if (dx > SWIPE_THRESHOLD)  prevShort(); // → swipe right = PREV
    };

    if (!articles || articles.length === 0) return null;

    const article       = articles[currentIndex];
    const numberMatch   = article.title.match(/(\d+%|\$\d+[MBT]?|\d+\s?billion|\d+\s?million)/i);
    const impactStat    = numberMatch ? numberMatch[0] : null;
    const swipeProgress = Math.min(Math.abs(dragX) / SWIPE_THRESHOLD, 1);
    const isNextSwipe   = dragX < -25;
    const isPrevSwipe   = dragX > 25;
    const canGoNext     = currentIndex < articles.length - 1;
    const canGoPrev     = currentIndex > 0;
    const articleBody    = article.content || article.description || '';
    const articleExcerpt = articleBody.length > 420 ? articleBody.substring(0, 420) + '...' : articleBody;
    const stopActionPropagation = (event) => {
        event.stopPropagation();
    };
    const openFullAnalysis = (event) => {
        event.preventDefault();
        event.stopPropagation();
        setIsDragging(false);
        setDragX(0);
        if (onArticleClick) onArticleClick(article);
    };

    /* ── Shared card inner content ───────────────── */
    const CardInner = () => (
        <Segment
            raised
            className="short-segment"
            style={{ borderTop: `8px solid ${article.impact_level === 'High' ? '#db2828' : '#2185d0'}` }}
        >
            <Label color={article.impact_level === 'High' ? 'red' : 'blue'} ribbon size="large">
                {article.impact_level} IMPACT
            </Label>

            <div className="short-content-wrapper">
                {impactStat ? (
                    <div className="impact-stat-hero">
                        <div className="stat-value">{impactStat}</div>
                        <div className="stat-context">{article.title.replace(impactStat, '___')}</div>
                    </div>
                ) : (
                    <Header as="h1" className="short-title">{article.title}</Header>
                )}

                <div className="short-ai-summary">
                    <Header as="h3"><Icon name="lightbulb" color="yellow" /> KEY INSIGHT</Header>
                    <p>
                        {(article.ai_summary && article.ai_summary !== 'Summary unavailable.')
                            ? article.ai_summary
                            : article.description || article.title}
                    </p>
                </div>

                {articleExcerpt && (
                    <div className="short-article-excerpt">
                        <Header as="h3"><Icon name="newspaper outline" /> ARTICLE</Header>
                        <p>{articleExcerpt}</p>
                    </div>
                )}

                <div className="short-meta">
                    <Label basic color="red">
                        <Icon name="shield" />
                        PREDOVEX INTELLIGENCE
                    </Label>
                    <Label basic><Icon name="globe" /> {(article.country || 'Global').toUpperCase()}</Label>
                    <Label basic><Icon name="wait" /> 30s read</Label>
                </div>
            </div>

            <div
                className="short-actions"
                onMouseDown={stopActionPropagation}
                onMouseMove={stopActionPropagation}
                onMouseUp={stopActionPropagation}
                onTouchStart={stopActionPropagation}
                onTouchMove={stopActionPropagation}
                onTouchEnd={stopActionPropagation}
            >
                <Button primary fluid size="huge" type="button" onClick={openFullAnalysis}>
                    <Icon name="expand" /> FULL ANALYSIS
                </Button>
                <div className="social-row">
                    <Button
                        circular color="twitter" icon="twitter"
                        onClick={() => window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(article.title + ' - via Predovex Intelligence Platform')}`)}
                    />
                    <Button
                        circular color="linkedin" icon="linkedin"
                        onClick={() => window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent('http://localhost:3000')}`)}
                    />
                    <Button
                        circular icon="share alternate"
                        onClick={() => {
                            const shareUrl = `http://localhost:3000/article/${article.govPulseID || Math.random().toString(36).substring(7)}`;
                            if (navigator.share) {
                                navigator.share({ title: article.title, url: shareUrl })
                                    .catch(function() {});
                            } else {
                                navigator.clipboard.writeText(shareUrl)
                                    .then(function() { alert('Link copied to clipboard!'); })
                                    .catch(function() { window.open(shareUrl, '_blank'); });
                            }
                        }}
                        title="Share article"
                    />
                </div>
            </div>
        </Segment>
    );

    /* ════════════════════════════════════════════════
       RENDER
       ════════════════════════════════════════════════ */
    return (
        <div
            className={`gov-shorts-container${isSwipeMode ? ' gov-shorts--swipe' : ''}`}
            onMouseMove={(e) => moveDrag(e.clientX)}
            onMouseUp={endDrag}
            onMouseLeave={endDrag}
        >

            {/* ─────────────────────────────────────────────
                NORMAL MODE  (≥ 1004 × 725)
                Up / Down button rail on the right
               ───────────────────────────────────────────── */}
            {!isSwipeMode && (
                <>
                    <div className="shorts-navigation">
                        <Button icon="chevron up"   circular onClick={prevShort} disabled={!canGoPrev} />
                        <span className="shorts-counter">{currentIndex + 1} / {articles.length}</span>
                        <Button icon="chevron down" circular onClick={nextShort} disabled={!canGoNext} />
                    </div>

                    <Transition
                        visible={visible}
                        animation={direction === 'up' ? 'slide up' : 'slide down'}
                        duration={300}
                    >
                        <div className="short-card">
                            <CardInner />
                        </div>
                    </Transition>
                </>
            )}

            {/* ─────────────────────────────────────────────
                SWIPE MODE  (< 1004 wide OR < 725 tall)
                Tinder-style drag card
               ───────────────────────────────────────────── */}
            {isSwipeMode && (
                <>
                    {/* Draggable card */}
                    <div
                        className="short-card short-card--swipeable"
                        style={{
                            transform: isDragging
                                ? `translateX(${dragX}px) rotate(${dragX * 0.025}deg)`
                                : 'translateX(0) rotate(0deg)',
                            transition: isDragging
                                ? 'none'
                                : 'transform 0.38s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                            cursor: isDragging ? 'grabbing' : 'grab',
                        }}
                        onTouchStart={(e) => startDrag(e.touches[0].clientX)}
                        onTouchMove={(e)  => moveDrag(e.touches[0].clientX)}
                        onTouchEnd={endDrag}
                        onMouseDown={(e) => { e.preventDefault(); startDrag(e.clientX); }}
                    >
                        {/* ← PREV overlay (dragging right) */}
                        {isPrevSwipe && (
                            <div
                                className="swipe-overlay swipe-overlay--right"
                                style={{ opacity: swipeProgress * 0.88 }}
                            >
                                <div className="swipe-badge swipe-badge--right">
                                    <span className="swipe-badge-arrow">←</span>
                                    <span className="swipe-badge-text">PREV</span>
                                </div>
                            </div>
                        )}

                        {/* NEXT → overlay (dragging left) */}
                        {isNextSwipe && (
                            <div
                                className="swipe-overlay swipe-overlay--left"
                                style={{ opacity: swipeProgress * 0.88 }}
                            >
                                <div className="swipe-badge swipe-badge--left">
                                    <span className="swipe-badge-text">NEXT</span>
                                    <span className="swipe-badge-arrow">→</span>
                                </div>
                            </div>
                        )}

                        <CardInner />
                    </div>

                    {/* Bottom bar — dots + prev/next taps */}
                    <div className="swipe-bottom-bar">
                        <button
                            className="swipe-nav-btn"
                            onClick={prevShort}
                            disabled={!canGoPrev}
                            aria-label="Previous"
                        >‹</button>

                        <div className="swipe-dots" role="tablist">
                            {articles.length <= 15
                                ? articles.map((_, i) => (
                                    <span
                                        key={i}
                                        role="tab"
                                        aria-selected={i === currentIndex}
                                        className={`swipe-dot${i === currentIndex ? ' swipe-dot--active' : ''}`}
                                        onClick={() => {
                                            setDirection(i > currentIndex ? 'up' : 'down');
                                            setCurrentIndex(i);
                                        }}
                                    />
                                ))
                                : <span className="swipe-counter-text">{currentIndex + 1} / {articles.length}</span>
                            }
                        </div>

                        <button
                            className="swipe-nav-btn"
                            onClick={nextShort}
                            disabled={!canGoNext}
                            aria-label="Next"
                        >›</button>
                    </div>

                    {/* Auto-fading swipe hint */}
                    {showHint && (
                        <div className="swipe-hint-bar" key="hint">
                            <Icon name="arrows alternate horizontal" size="small" />
                            &nbsp;swipe left / right to navigate
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default GovShorts;
