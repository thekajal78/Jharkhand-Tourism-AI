# API Documentation - Jharkhand Tourism AI Platform

## Base URL
- Development: `http://localhost:8000/api/v1`
- Production: `https://api.jharkhand-tourism.com/api/v1`

## Authentication

All protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Core Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `GET /auth/profile` - Get user profile

### Destinations
- `GET /destinations/` - List destinations
- `GET /destinations/{id}` - Get destination details
- `POST /destinations/` - Create destination (admin)
- `PUT /destinations/{id}` - Update destination (admin)

### Visual Search (CLIP)
- `POST /images/visual-search` - Search by image upload
- `POST /images/text-search` - Search by text description
- `GET /images/similar/{image_id}` - Get similar images

### Recommendations
- `GET /recommendations/personalized` - Get personalized recommendations
- `GET /recommendations/trending` - Get trending destinations
- `GET /recommendations/similar/{destination_id}` - Get similar destinations

### Chatbot
- `POST /chatbot/message` - Send message to chatbot
- `GET /chatbot/history` - Get conversation history

### Analytics
- `GET /analytics/overview` - Platform analytics overview
- `GET /analytics/destinations` - Destination analytics
- `GET /analytics/users` - User analytics

## Response Format

All API responses follow this format:
```json
{
  "success": true,
  "data": {},
  "message": "Success",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Error Handling

Error responses include:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {}
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Interactive API Documentation

Visit `/docs` for Swagger UI documentation and `/redoc` for ReDoc documentation when running the application.