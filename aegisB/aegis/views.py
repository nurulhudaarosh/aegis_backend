from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import EmergencyContact
from .serializers import (
    EmergencyContactSerializer, 
    EmergencyContactCreateSerializer,
    UserWithContactsSerializer,
    PhoneLookupSerializer,
    UserLookupSerializer
)

User = get_user_model()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def lookup_phone(request):
    """Look up user by phone number and return their details if found"""
    serializer = PhoneLookupSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone_number = serializer.validated_data['phone']
    
    try:
        # Clean phone number for comparison (remove spaces, dashes, etc.)
        clean_phone = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Check if user exists with this phone number (case-insensitive partial match)
        users = User.objects.filter(phone__icontains=clean_phone).exclude(id=request.user.id)
        
        if users.exists():
            # Find the best match (exact match or closest)
            exact_match = users.filter(phone__iexact=clean_phone).first()
            user = exact_match or users.first()
            
            user_serializer = UserLookupSerializer(user)
            
            # Check if this user is already added as a contact
            existing_contact = EmergencyContact.objects.filter(
                user=request.user, 
                phone__icontains=clean_phone
            ).exists()
            
            return Response({
                'found': True,
                'user': user_serializer.data,
                'already_added': existing_contact,
                'exact_match': exact_match is not None
            })
        
        return Response({
            'found': False,
            'message': 'No user found with this phone number'
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def emergency_contacts_list(request):
    if request.method == 'GET':
        contacts = EmergencyContact.objects.filter(user=request.user)
        serializer = EmergencyContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = EmergencyContactCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Check if contact already exists
                phone = serializer.validated_data['phone']
                existing_contact = EmergencyContact.objects.filter(
                    user=request.user, 
                    phone__iexact=phone
                ).exists()
                
                if existing_contact:
                    return Response(
                        {'error': 'A contact with this phone number already exists'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                contact = serializer.save(user=request.user)
                full_serializer = EmergencyContactSerializer(contact)
                return Response(full_serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def emergency_contact_detail(request, pk):
    try:
        contact = EmergencyContact.objects.get(pk=pk, user=request.user)
    except EmergencyContact.DoesNotExist:
        return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = EmergencyContactSerializer(contact)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        serializer = EmergencyContactCreateSerializer(
            contact, 
            data=request.data, 
            partial=request.method == 'PATCH'
        )
        if serializer.is_valid():
            try:
                # Check for duplicate phone number when updating
                if 'phone' in serializer.validated_data:
                    phone = serializer.validated_data['phone']
                    duplicate_exists = EmergencyContact.objects.filter(
                        user=request.user, 
                        phone__iexact=phone
                    ).exclude(pk=pk).exists()
                    
                    if duplicate_exists:
                        return Response(
                            {'error': 'Another contact with this phone number already exists'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                contact = serializer.save()
                full_serializer = EmergencyContactSerializer(contact)
                return Response(full_serializer.data)
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        contact.delete()
        return Response({'message': 'Contact deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_emergency_alert(request, pk):
    try:
        contact = EmergencyContact.objects.get(pk=pk, user=request.user)
        # Here you would integrate with your alert service (Twilio, etc.)
        # For now, just return a success message
        print('test successful')
        return Response({
            'message': f'Test alert sent to {contact.name}',
            'contact': EmergencyContactSerializer(contact).data
        })
    except EmergencyContact.DoesNotExist:
        return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_emergency_contact(request, pk):
    """Alternative delete endpoint using POST method"""
    try:
        contact = EmergencyContact.objects.get(pk=pk, user=request.user)
        contact_name = contact.name
        contact.delete()
        return Response({
            'message': f'Contact {contact_name} deleted successfully',
            'deleted_contact_id': pk
        }, status=status.HTTP_200_OK)
    except EmergencyContact.DoesNotExist:
        return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_emergency_info(request):
    user = request.user
    serializer = UserWithContactsSerializer(user)
    return Response(serializer.data)