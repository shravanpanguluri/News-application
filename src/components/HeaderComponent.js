import React from 'react';

export default function HeaderComponent() {
	return (
		<div className="dashboard-hero">
			<div className="dashboard-hero__copy">
				<div className="dashboard-hero__eyebrow">
					<span className="dashboard-hero__pulse" />
					LIVE INTELLIGENCE BRIEFING
				</div>
				<h1>Know what moves<br /><em>the world next.</em></h1>
				<p>Government signals, market pressure, and the stories shaping decisions—curated in one calm workspace.</p>
			</div>
			<div className="dashboard-hero__aside">
				<div className="dashboard-hero__date">PREDOVEX / DAILY EDITION</div>
				<div className="dashboard-hero__signal">
					<span className="dashboard-hero__signal-dot" />
					<span>Live feeds connected</span>
				</div>
				<div className="dashboard-hero__hint">Tap a sector below to focus your brief.</div>
			</div>
		</div>
	);
}
