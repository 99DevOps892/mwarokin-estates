-- ============================================================================
-- MWAROKIN ESTATES — SEED DATA (optional, safe to run multiple times)
-- Run AFTER schema.sql, functions.sql, policies.sql
-- ============================================================================

-- Exchange rates (KES base) — overwrite with real rates via the currency Edge Function
INSERT INTO exchange_rates (base_currency, target_currency, rate, source) VALUES
  ('KES','USD', 0.0077, 'seed'),
  ('KES','EUR', 0.0071, 'seed'),
  ('KES','GBP', 0.0060, 'seed')
ON CONFLICT (base_currency, target_currency)
DO UPDATE SET rate = EXCLUDED.rate, previous_rate = exchange_rates.rate, source = EXCLUDED.source;

-- Core translations (English)
INSERT INTO translations (language_code, namespace, key, value) VALUES
  ('en','common','app_name','Mwarokin Estates'),
  ('en','common','tagline','Premier Property Management & Real Estate'),
  ('en','common','browse_properties','Browse Properties'),
  ('en','common','login','Login'),
  ('en','common','register','Register'),
  ('en','common','logout','Logout'),
  ('en','common','dashboard','Dashboard'),
  ('en','common','admin','Admin Panel'),
  ('en','common','profile','Profile'),
  ('en','common','pay_rent','Pay Rent'),
  ('en','common','report_issue','Report an Issue'),
  ('en','common','contact_us','Contact Us'),
  ('en','common','loading','Loading...'),
  ('en','common','available','Available'),
  ('en','common','rented','Rented'),
  ('en','common','under_maintenance','Under Maintenance'),
  ('en','common','sold','Sold'),
  ('en','common','price','Price'),
  ('en','common','location','Location'),
  ('en','common','bedrooms','Bedrooms'),
  ('en','common','bathrooms','Bathrooms'),
  ('en','common','view_details','View Details'),
  ('en','common','search','Search'),
  ('en','common','all','All'),
  ('en','common','house','House'),
  ('en','common','apartment','Apartment'),
  ('en','common','land','Land'),
  ('en','common','commercial','Commercial'),
  ('en','common','villa','Villa'),
  ('en','common','bedsitter','Bedsitter'),
  ('en','common','bungalow','Bungalow'),
  ('en','common','platform_fee','Platform Fee (5%)'),
  ('en','common','landlord_gets','Landlord receives'),
  ('en','common','my_notifications','My Notifications'),
  ('en','common','no_properties','No properties found.'),
  ('en','common','welcome_back','Welcome back'),
  ('en','common','make_payment','Make Payment')
ON CONFLICT (language_code, namespace, key) DO NOTHING;

-- Swahili translations (core)
INSERT INTO translations (language_code, namespace, key, value) VALUES
  ('sw','common','app_name','Mwarokin Estates'),
  ('sw','common','tagline','Usimamizi Bora wa Mali Isiyohamishika'),
  ('sw','common','browse_properties','Tazama Majengo'),
  ('sw','common','login','Ingia'),
  ('sw','common','register','Jisajili'),
  ('sw','common','logout','Toka'),
  ('sw','common','dashboard','Dashibodi'),
  ('sw','common','admin','Jopo la Usimamizi'),
  ('sw','common','profile','Wasifu'),
  ('sw','common','pay_rent','Lipa Kodi'),
  ('sw','common','report_issue','Ripoti Tatizo'),
  ('sw','common','contact_us','Wasiliana Nasi'),
  ('sw','common','loading','Inapakia...'),
  ('sw','common','available','Inapatikana'),
  ('sw','common','rented','Imekodiwa'),
  ('sw','common','under_maintenance','Inarekebishwa'),
  ('sw','common','sold','Imeuzwa'),
  ('sw','common','price','Bei'),
  ('sw','common','location','Eneo'),
  ('sw','common','bedrooms','Vyumba vya Kulala'),
  ('sw','common','bathrooms','Bafu'),
  ('sw','common','view_details','Tazama Maelezo'),
  ('sw','common','search','Tafuta'),
  ('sw','common','all','Yote'),
  ('sw','common','house','Nyumba'),
  ('sw','common','apartment','Fleti'),
  ('sw','common','land','Ardhi'),
  ('sw','common','commercial','Biashara'),
  ('sw','common','villa','Villa'),
  ('sw','common','bedsitter','Bedsitter'),
  ('sw','common','bungalow','Bungalow'),
  ('sw','common','platform_fee','Ada ya Jukwaa (5%)'),
  ('sw','common','landlord_gets','Mwenye nyumba anapokea'),
  ('sw','common','my_notifications','Arifa Zangu'),
  ('sw','common','no_properties','Hakuna majengo yaliyopatikana.'),
  ('sw','common','welcome_back','Karibu tena'),
  ('sw','common','make_payment','Fanya Malipo')
ON CONFLICT (language_code, namespace, key) DO NOTHING;

-- Sample properties (staff/admin can replace with real inventory)
INSERT INTO properties (title, slug, description, property_type, status, price, deposit, bedrooms, bathrooms, area_sqft, location, city, county, country, amenities, images, is_featured)
SELECT * FROM (VALUES
  ('Sunrise Executive Apartment','sunrise-executive-apartment','Modern 2-bedroom apartment with city views, gym and secure parking.','apartment','available',45000.00,90000.00,2,2,1100,'Kilimani, Nairobi','Nairobi','Nairobi','Kenya','["Gym","WiFi","Parking","24/7 Security","Backup Generator","Water Heater"]','["https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800","https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800"]',true),
  ('Green Valley Family House','green-valley-family-house','Spacious 4-bedroom family home with a large garden and borehole.','house','available',85000.00,170000.00,4,3,2400,'Karen, Nairobi','Nairobi','Nairobi','Kenya','["Garden","Borehole","Double Garage","Solar Water Heater","Servants Quarter"]','["https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800","https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800"]',true),
  ('CBD Office Suite 7','cbd-office-suite-7','Grade-A commercial office space in the heart of Nairobi CBD.','commercial','available',120000.00,240000.00,0,2,1800,'Upper Hill, Nairobi','Nairobi','Nairobi','Kenya','["Fibre Internet","Boardroom","Lift Access","Generator","Reception"]','["https://images.unsplash.com/photo-1497366754035-f200968a6e72?w=800"]',false),
  ('Riverside Studio Unit','riverside-studio-unit','Fully furnished studio ideal for professionals, near Riverside Drive.','bedsitter','rented',28000.00,56000.00,1,1,450,'Riverside, Nairobi','Nairobi','Nairobi','Kenya','["Furnished","Water Included","WiFi","Cleaner"]','["https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=800"]',false)
) AS v(title, slug, description, property_type, status, price, deposit, bedrooms, bathrooms, area_sqft, location, city, county, country, amenities, images, is_featured)
WHERE NOT EXISTS (SELECT 1 FROM properties);