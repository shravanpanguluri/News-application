import React, { useState } from 'react';
import { Pagination } from 'semantic-ui-react';
import ArticleViewer from './ArticleViewer/ArticleViewer';

export default function NewsCards(props) {
	const [selectedArticle, setSelectedArticle] = useState(null);
	const [viewerOpen, setViewerOpen] = useState(false);
	const [currentPage, setCurrentPage] = useState(1);
	const articlesPerPage = 9;

	const handleCardClick = (article) => {
		setSelectedArticle(article);
		setViewerOpen(true);
	};

	// Calculate pagination
	const totalArticles = props.articles ? props.articles.length : 0;
	const totalPages = Math.ceil(totalArticles / articlesPerPage);
	const indexOfLastArticle = currentPage * articlesPerPage;
	const indexOfFirstArticle = indexOfLastArticle - articlesPerPage;
	const currentArticles = props.articles
		? props.articles.slice(indexOfFirstArticle, indexOfLastArticle)
		: [];

	const handlePageChange = (e, { activePage }) => {
		setCurrentPage(activePage);
		window.scrollTo({ top: 0, behavior: 'smooth' });
	};

	return (
		<div className="news-container">
			<div className="news-grid">
				{currentArticles && currentArticles.length > 0
					? currentArticles.map((article, idx) => (
							<div key={idx} className="news-card-wrapper" onClick={() => handleCardClick(article)}>
								<div className="news-card">
									<div className="news-card-image">
										{article.urlToImage ? (
											<img src={article.urlToImage} alt={article.title} />
										) : (
											<div className="news-card-image-placeholder">
												<i className="newspaper icon"></i>
											</div>
										)}
									</div>
									<div className="news-card-content">
										<h3 className="news-card-title">
											{article.title.length > 60
												? article.title.substr(0, 60) + '...'
												: article.title}
										</h3>
										{article.description && (
											<p className="news-card-description">
												{article.description.length > 100
													? article.description.substr(0, 100) + '...'
													: article.description}
											</p>
										)}
										<div className="news-card-meta">
											<span className="news-card-source">
												{article.source && article.source.name
													? article.source.name
													: 'News'}
											</span>
											<span className="news-card-date">
												{new Date(article.publishedAt).toLocaleDateString()}
											</span>
										</div>
									</div>
								</div>
							</div>
					  ))
					: null}
			</div>

			{totalPages > 1 && (
				<div className="pagination-container">
					<Pagination
						activePage={currentPage}
						onPageChange={handlePageChange}
						totalPages={totalPages}
						size="large"
						firstItem
						lastItem
						secondary
						pointing
						boundaryRange={1}
						siblingRange={2}
					/>
					<p className="pagination-info">
						Page {currentPage} of {totalPages} | Showing {currentArticles.length} of{' '}
						{totalArticles} articles
					</p>
				</div>
			)}

			<ArticleViewer
				article={selectedArticle}
				open={viewerOpen}
				onClose={() => setViewerOpen(false)}
			/>
		</div>
	);
}
