import React, { useRef, useState } from 'react';
import { Icon } from 'semantic-ui-react';
import './PullToRefresh.css';

var THRESHOLD = 64;

export default function PullToRefresh(props) {
	var startY = useRef(null);
	var pulling = useRef(false);
	var [pullDist, setPullDist] = useState(0);
	var [refreshing, setRefreshing] = useState(false);

	function onTouchStart(e) {
		var el = e.currentTarget;
		if (el.scrollTop > 0) return;
		startY.current = e.touches[0].clientY;
		pulling.current = true;
	}

	function onTouchMove(e) {
		if (!pulling.current || startY.current === null) return;
		var el = e.currentTarget;
		if (el.scrollTop > 0) { pulling.current = false; setPullDist(0); return; }
		var dy = e.touches[0].clientY - startY.current;
		if (dy < 0) { setPullDist(0); return; }
		e.preventDefault();
		setPullDist(Math.min(dy, THRESHOLD * 1.5));
	}

	function onTouchEnd() {
		if (!pulling.current) return;
		pulling.current = false;
		if (pullDist >= THRESHOLD && !refreshing && props.onRefresh) {
			setRefreshing(true);
			hapticMedium();
			Promise.resolve(props.onRefresh()).then(function() {
				setRefreshing(false);
				setPullDist(0);
			}).catch(function() {
				setRefreshing(false);
				setPullDist(0);
			});
		} else {
			setPullDist(0);
		}
		startY.current = null;
	}

	function hapticMedium() {
		try {
			import('@capacitor/haptics').then(function(m) {
				m.Haptics.impact({ style: m.ImpactStyle.Medium }).catch(function() {});
			}).catch(function() {});
		} catch (e) {}
	}

	var indicatorStyle = {
		transform: 'translateY(' + (refreshing ? THRESHOLD : Math.min(pullDist, THRESHOLD)) + 'px)',
		opacity: refreshing ? 1 : Math.min(pullDist / THRESHOLD, 1),
	};

	var contentStyle = {
		transform: 'translateY(' + (refreshing ? THRESHOLD : Math.min(pullDist, THRESHOLD)) + 'px)',
		transition: pulling.current ? 'none' : 'transform 0.25s ease',
	};

	return (
		<div
			className="ptr-root"
			onTouchStart={onTouchStart}
			onTouchMove={onTouchMove}
			onTouchEnd={onTouchEnd}
		>
			<div className="ptr-indicator" style={indicatorStyle}>
				<Icon
					name={refreshing ? 'spinner' : 'arrow down'}
					loading={refreshing}
					style={{ color: '#c8553d' }}
				/>
			</div>
			<div style={contentStyle}>
				{props.children}
			</div>
		</div>
	);
}
