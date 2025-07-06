def search_health_worker_query_set(query_set, search_text):
    """Enhanced search that handles doctor titles and uses OR logic for better matching"""
    
    # Clean up search text and remove common titles
    cleaned_search = search_text.strip().lower()
    
    # Remove common doctor titles
    titles_to_remove = ['dr.', 'dr', 'doctor', 'prof.', 'prof', 'professor']
    for title in titles_to_remove:
        if cleaned_search.startswith(title + ' '):
            cleaned_search = cleaned_search[len(title):].strip()
        elif cleaned_search.startswith(title):
            cleaned_search = cleaned_search[len(title):].strip()
    
    # If after removing titles there's nothing left, return all
    if not cleaned_search:
        return query_set
    
    # Split into search terms
    search_items = list(
        filter(
            lambda x: len(x) > 0,
            map(lambda x: x.strip(), cleaned_search.split(" ")),
        )
    )
    
    if not search_items:
        return query_set
    
    # Build search query with OR logic for each term
    search_query = None
    
    for search_item in search_items:
        # Create OR conditions for this search term
        term_query = (
            Q(first_name__icontains=search_item) |
            Q(last_name__icontains=search_item) |
            Q(middle_name__icontains=search_item) |
            Q(primary_specialty__name__icontains=search_item)
        )
        
        # Combine with previous terms using AND
        # (each term must match at least one field, but different terms can match different fields)
        if search_query is None:
            search_query = term_query
        else:
            search_query = search_query & term_query
    
    return query_set.filter(search_query)


# Alternative simpler version - uses OR logic for all terms
def search_health_worker_query_set_simple(query_set, search_text):
    """Simplified search with OR logic - any term can match any field"""
    
    # Clean up search text and remove common titles
    cleaned_search = search_text.strip().lower()
    
    # Remove common doctor titles
    titles_to_remove = ['dr.', 'dr', 'doctor', 'prof.', 'prof', 'professor']
    for title in titles_to_remove:
        if cleaned_search.startswith(title + ' '):
            cleaned_search = cleaned_search[len(title):].strip()
    
    if not cleaned_search:
        return query_set
    
    # Split into search terms
    search_items = list(
        filter(
            lambda x: len(x) > 0,
            map(lambda x: x.strip(), cleaned_search.split(" ")),
        )
    )
    
    if not search_items:
        return query_set
    
    # Build search query with OR logic for all terms and fields
    search_query = None
    
    for search_item in search_items:
        term_query = (
            Q(first_name__icontains=search_item) |
            Q(last_name__icontains=search_item) |
            Q(middle_name__icontains=search_item) |
            Q(primary_specialty__name__icontains=search_item)
        )
        
        # Combine with previous terms using OR (any term can match)
        if search_query is None:
            search_query = term_query
        else:
            search_query = search_query | term_query
    
    return query_set.filter(search_query)


# For debugging - let's also create a version that shows what it's doing
def search_health_worker_query_set_debug(query_set, search_text):
    """Debug version that shows what's happening"""
    
    print(f"🔍 SEARCH DEBUG: Original search text: '{search_text}'")
    
    # Clean up search text and remove common titles
    cleaned_search = search_text.strip().lower()
    original_cleaned = cleaned_search
    
    # Remove common doctor titles
    titles_to_remove = ['dr.', 'dr', 'doctor', 'prof.', 'prof', 'professor']
    for title in titles_to_remove:
        if cleaned_search.startswith(title + ' '):
            cleaned_search = cleaned_search[len(title):].strip()
            print(f"🔍 SEARCH DEBUG: Removed title '{title}', now: '{cleaned_search}'")
            break
    
    if not cleaned_search:
        print(f"🔍 SEARCH DEBUG: No search terms left after removing title")
        return query_set
    
    # Split into search terms
    search_items = list(
        filter(
            lambda x: len(x) > 0,
            map(lambda x: x.strip(), cleaned_search.split(" ")),
        )
    )
    
    print(f"🔍 SEARCH DEBUG: Search terms: {search_items}")
    
    if not search_items:
        return query_set
    
    # Use simple OR logic for all terms
    search_query = None
    
    for search_item in search_items:
        term_query = (
            Q(first_name__icontains=search_item) |
            Q(last_name__icontains=search_item) |
            Q(middle_name__icontains=search_item) |
            Q(primary_specialty__name__icontains=search_item)
        )
        
        if search_query is None:
            search_query = term_query
        else:
            search_query = search_query | term_query
    
    result = query_set.filter(search_query)
    print(f"🔍 SEARCH DEBUG: Found {result.count()} doctors after search")
    
    return result