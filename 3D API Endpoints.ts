// Authentication
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/auth/me

// Projects
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/:id
PUT    /api/v1/projects/:id
DELETE /api/v1/projects/:id
GET    /api/v1/projects/:id/export?format=gltf|usd|obj

// Design Elements
GET    /api/v1/projects/:id/elements
POST   /api/v1/projects/:id/elements
PUT    /api/v1/projects/:id/elements/:elementId
DELETE /api/v1/projects/:id/elements/:elementId

// AI Generation
POST   /api/v1/ai/generate-design
POST   /api/v1/ai/suggest-layout
GET    /api/v1/ai/materials/:style

// Rendering
POST   /api/v1/render/queue
GET    /api/v1/render/jobs/:jobId
GET    /api/v1/render/presets

// Collaboration
GET    /api/v1/projects/:id/collaborators
POST   /api/v1/projects/:id/invite