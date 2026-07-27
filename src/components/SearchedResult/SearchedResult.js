import React from 'react';
import { Item, Label, Popup, Icon } from 'semantic-ui-react';

export default function SearchedResult(props) {
	const safeFormatDate = (dateVal) => {
		if (!dateVal) return 'Recently';
		try {
			const d = new Date(dateVal);
			return isNaN(d.getTime()) ? 'Recently' : d.toDateString();
		} catch (e) {
			return 'Recently';
		}
	};

	const handleItemClick = (e, story) => {
		if (e) {
			e.preventDefault();
			e.stopPropagation();
		}
		if (props.onArticleClick) {
			props.onArticleClick(story);
		}
	};

	return (
		<div style={{ margin: '20px' }}>
			<Item.Group divided>
				{props.result.length > 0
					? props.result.map((story, index) => (
							<Item key={index} onClick={(e) => handleItemClick(e, story)} style={{ cursor: 'pointer' }}>
								<Item.Image src={story.urlToImage || 'https://via.placeholder.com/150'} size="small" />

								<Item.Content>
									<Item.Header style={{ color: '#2185d0' }}>{story.title}</Item.Header>
									<Item.Meta>
										<span className='cinema'>
											<Icon name="calendar" /> {safeFormatDate(story.publishedAt)}
										</span>
									</Item.Meta>
									<Item.Description>{story.description}</Item.Description>
									<Item.Extra>
										<Popup
											content='Author'
											trigger={
												<Label size="tiny">{story.author ? story.author : 'N/A'}</Label>
											}
										/>
										<Popup
											content='Source'
											trigger={
												<Label
													size="tiny"
													icon='globe'
													content={
														story.source && story.source.name ? story.source.name : 'N/A'
													}
												/>
											}
										/>
									</Item.Extra>
								</Item.Content>
							</Item>
					  ))
					: ''}
			</Item.Group>
		</div>
	);
}
