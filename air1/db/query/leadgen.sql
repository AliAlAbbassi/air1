-- name: get_software_product_by_slug^
SELECT id, name, slug, website, detection_patterns
FROM software_products
WHERE slug = :slug;

-- name: get_software_product_by_id^
SELECT id, name, slug, website, detection_patterns
FROM software_products
WHERE id = :product_id;

-- name: insert_software_product<!
INSERT INTO software_products (name, slug, website, detection_patterns)
VALUES (:name, :slug, :website, :detection_patterns::jsonb)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website,
    detection_patterns = EXCLUDED.detection_patterns,
    updated_at = NOW()
RETURNING id, name, slug;

-- name: insert_lead_search<!
INSERT INTO lead_searches (user_id, software_product_id, search_params, status)
VALUES (:user_id, :software_product_id, :search_params::jsonb, :status)
RETURNING id;

-- name: update_lead_search_status!
UPDATE lead_searches
SET status = :status, stats = :stats::jsonb, updated_at = NOW()
WHERE id = :search_id;

-- name: get_lead_search^
SELECT id, user_id, software_product_id, search_params, status, stats, created_at
FROM lead_searches
WHERE id = :search_id;

-- name: get_pending_leads
SELECT id, name, website
FROM search_leads
WHERE lead_search_id = :search_id
  AND detection_status = 'pending'
  AND website IS NOT NULL
  AND website != '';

-- name: update_lead_detection!
UPDATE search_leads
SET detection_status = :detection_status,
    detected_software = :detected_software,
    detection_method = :detection_method,
    detection_details = :detection_details::jsonb,
    detected_at = CASE WHEN :detection_status = 'detected' THEN NOW() ELSE NULL END
WHERE id = :lead_id;

-- name: get_search_results
SELECT id, name, website, phone, email, address, city, state, country,
       latitude, longitude, google_place_id, source,
       detection_status, detected_software, detection_method, detection_details
FROM search_leads
WHERE lead_search_id = :search_id
ORDER BY detection_status = 'detected' DESC, name;

-- name: get_detected_leads
SELECT id, name, website, phone, email, address, city, state, country,
       latitude, longitude, detected_software, detection_method, detection_details
FROM search_leads
WHERE lead_search_id = :search_id
  AND detection_status = 'detected'
ORDER BY name;

-- name: count_search_leads$
SELECT COUNT(*) FROM search_leads WHERE lead_search_id = :search_id;

-- name: count_detected_leads$
SELECT COUNT(*) FROM search_leads
WHERE lead_search_id = :search_id AND detection_status = 'detected';
