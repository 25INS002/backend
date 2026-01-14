import os
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings

# Import the same auth used by media_app
from media_app.auth import CookieJWTAuthentication


# Path to the backend content directory
CONTENT_BASE_PATH = os.path.join(settings.BASE_DIR, 'content')

# Define the content categories and their files
CONTENT_STRUCTURE = {
    'home': {
        'name': 'Home Page',
        'files': ['team.json', 'hero.json', 'about.json', 'services.json', 'prototypes.json', 'history.json', 'meta.json']
    },
    'about': {
        'name': 'About Page',
        'files': ['full_team.json']
    },
    'prototype': {
        'name': 'Prototypes',
        'files': ['main.json']
    }
}


class ContentListView(APIView):
    """List all content categories and their files"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        result = []
        
        for category_id, category_info in CONTENT_STRUCTURE.items():
            category_path = os.path.join(CONTENT_BASE_PATH, category_id)
            
            files = []
            if os.path.exists(category_path):
                # Get actual files that exist
                for filename in category_info['files']:
                    file_path = os.path.join(category_path, filename)
                    if os.path.exists(file_path):
                        files.append({
                            'name': filename,
                            'displayName': filename.replace('.json', '').replace('_', ' ').title()
                        })
            
            result.append({
                'id': category_id,
                'name': category_info['name'],
                'files': files
            })
        
        return Response(result)


class ContentReadView(APIView):
    """Read a specific JSON content file"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        category = request.query_params.get('category')
        filename = request.query_params.get('file')
        
        if not category or not filename:
            return Response(
                {'error': 'Both category and file parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate category
        if category not in CONTENT_STRUCTURE:
            return Response(
                {'error': f'Invalid category: {category}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Security: ensure filename doesn't contain path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return Response(
                {'error': 'Invalid filename'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_path = os.path.join(CONTENT_BASE_PATH, category, filename)
        
        if not os.path.exists(file_path):
            return Response(
                {'error': f'File not found: {filename}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            return Response({
                'category': category,
                'file': filename,
                'content': content
            })
        except json.JSONDecodeError as e:
            return Response(
                {'error': f'Invalid JSON in file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContentUpdateView(APIView):
    """Update a JSON content file"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        category = request.data.get('category')
        filename = request.data.get('file')
        content = request.data.get('content')
        
        if not category or not filename or content is None:
            return Response(
                {'error': 'category, file, and content are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate category
        if category not in CONTENT_STRUCTURE:
            return Response(
                {'error': f'Invalid category: {category}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Security: ensure filename doesn't contain path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return Response(
                {'error': 'Invalid filename'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_path = os.path.join(CONTENT_BASE_PATH, category, filename)
        
        if not os.path.exists(file_path):
            return Response(
                {'error': f'File not found: {filename}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Validate that content is valid JSON by attempting to serialize it
            json_str = json.dumps(content, indent=4, ensure_ascii=False)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            return Response({
                'success': True,
                'message': f'Successfully updated {filename}'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
