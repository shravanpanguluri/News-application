import React from 'react';
import { Dropdown, Grid } from 'semantic-ui-react';

const categories = [
	{ key: 'all', text: '📰 All News', value: 'all' },
	{ key: 'general', text: '🌍 General', value: 'general' },
	{ key: 'markets', text: '💰 Markets', value: 'markets' },
	{ key: 'business', text: '💼 Business', value: 'business' },
	{ key: 'technology', text: '💻 Technology', value: 'technology' },
	{ key: 'entertainment', text: '🎬 Entertainment', value: 'entertainment' },
	{ key: 'sports', text: '⚽ Sports', value: 'sports' },
	{ key: 'science', text: '🔬 Science', value: 'science' },
	{ key: 'health', text: '🏥 Health', value: 'health' },
];

const CategoryFilter = ({ value, onChange }) => {
	return (
		<Grid>
			<Grid.Column>
				<Dropdown
					placeholder="Select Category"
					fluid
					selection
					options={categories}
					value={value}
					onChange={onChange}
					size="large"
				/>
			</Grid.Column>
		</Grid>
	);
};

export default CategoryFilter;
