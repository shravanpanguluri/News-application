import React from 'react';
import { Search, Grid, Header, Segment } from 'semantic-ui-react';

export default function SearchComponent(props) {
	return (
		<Grid>
			<Grid.Column>
				<Search
					onSearchChange={props.onSearchChange}
					value={props.value}
					onKeyDown={props.searchOnEnter}
					fluid
					size='big'
					minCharacters={2}
					noResultsMessage={null}
					open={false}
				/>
			</Grid.Column>
		</Grid>
	);
}
