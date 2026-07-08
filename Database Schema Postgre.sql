-- Projects Table
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  owner_id UUID REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  version INT DEFAULT 1,
  thumbnail_url VARCHAR(500),
  is_public BOOLEAN DEFAULT false,
  geo_location POINT, -- PostGIS for real-world placement
  metadata JSONB -- Store project settings
);

-- Design Elements Table (Spatial)
CREATE TABLE design_elements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  element_type VARCHAR(50) NOT NULL, -- wall, floor, furniture, etc.
  geometry GEOMETRY(GeometryZ, 4326), -- PostGIS 3D geometry
  material JSONB,
  properties JSONB,
  layer INT DEFAULT 0,
  created_by UUID REFERENCES users(id)
);

-- Users Table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  plan_type VARCHAR(50) DEFAULT 'free',
  render_credits INT DEFAULT 10,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Render Jobs Table
CREATE TABLE render_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  status VARCHAR(50) DEFAULT 'pending',
  output_url VARCHAR(500),
  settings JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);