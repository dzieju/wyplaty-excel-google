import React, { useState } from 'react';

function Search() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    
    // Simulate search functionality - in a real implementation,
    // this would call an API endpoint to search through the sheets data
    setTimeout(() => {
      // Mock search results for demonstration
      setSearchResults([
        {
          id: 1,
          title: 'Example Result 1',
          description: `Found match for "${searchQuery}" in Sheet 1`,
          sheet: 'Sheet 1',
          row: 5
        },
        {
          id: 2,
          title: 'Example Result 2',
          description: `Found match for "${searchQuery}" in Sheet 2`,
          sheet: 'Sheet 2',
          row: 12
        }
      ]);
      setIsSearching(false);
    }, 1000);
  };

  return (
    <div className="container">
      <h1 className="page-title">🔍 Search Data</h1>

      <div className="card">
        <h2 className="card-title">Search in Google Sheets</h2>
        <p className="description">
          Search through your accessible Google Sheets data. Make sure you have configured your service account first.
        </p>
        
        <form onSubmit={handleSearch}>
          <div className="form-group">
            <label htmlFor="search-input">Search Query</label>
            <input
              id="search-input"
              type="text"
              className="form-input"
              placeholder="Enter your search query..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button type="submit" className="btn" disabled={isSearching || !searchQuery.trim()}>
            {isSearching ? (
              <>
                <span className="loader"></span>
                Searching...
              </>
            ) : (
              'Search'
            )}
          </button>
        </form>
      </div>

      {searchResults.length > 0 && (
        <div className="card">
          <h2 className="card-title">Search Results</h2>
          <div className="search-results">
            {searchResults.map((result) => (
              <div key={result.id} className="search-result-item">
                <h3>{result.title}</h3>
                <p>{result.description}</p>
                <p>
                  <strong>Sheet:</strong> {result.sheet} | <strong>Row:</strong> {result.row}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {searchResults.length === 0 && searchQuery && !isSearching && (
        <div className="card">
          <p className="description">No results found. Try a different search query.</p>
        </div>
      )}
    </div>
  );
}

export default Search;
