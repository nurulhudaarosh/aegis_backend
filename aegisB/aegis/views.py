from rest_framework import status,viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


from .models import (
    EmergencyContact,
    ResourceCategory,
    LearningResource,
    UserProgress,
    UserQuizAttempt,
    QuizQuestion,
    QuizOption,
    IncidentReport, 
    IncidentUpdate,
)

from .serializers import (
    EmergencyContactSerializer, 
    EmergencyContactCreateSerializer,
    UserWithContactsSerializer,
    PhoneLookupSerializer,
    UserLookupSerializer,
    ResourceCategorySerializer,
    LearningResourceSerializer,
    UserProgressSerializer,
    QuizSubmissionSerializer,
    UserQuizAttemptSerializer,
    ExternalLinkSerializer,
    QuizQuestionSerializer,
    QuizOptionSerializer,
    IncidentReportSerializer,
    IncidentReportCreateSerializer,
    MediaUploadSerializer,
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


# learn......................

@api_view(['GET'])
@permission_classes([AllowAny])
def resource_categories(request):
    categories = ResourceCategory.objects.filter(is_active=True).annotate(
        resource_count=Count('resources', filter=Q(resources__is_published=True))
    ).order_by('order', 'name')
    
    serializer = ResourceCategorySerializer(categories, many=True)
    return Response(serializer.data)


class LearningResourceListView(ListAPIView):
    serializer_class = LearningResourceSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = LearningResource.objects.filter(is_published=True)
        
        category = self.request.query_params.get('category')
        if category and category.lower() != 'all':
            queryset = queryset.filter(category__name__iexact=category)
        
        resource_type = self.request.query_params.get('type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(content__icontains=search)
            )
        
        return queryset.select_related('category').prefetch_related(
            'external_links', 'quiz_questions__options'
        ).order_by('order', 'created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context



class LearningResourceDetailView(RetrieveAPIView):
    serializer_class = LearningResourceSerializer
    permission_classes = [AllowAny]
    queryset = LearningResource.objects.filter(is_published=True)
    lookup_field = 'id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Track user progress if authenticated
        if request.user.is_authenticated:
            progress, _ = UserProgress.objects.get_or_create(
                user=request.user,
                resource=instance
            )
            if not progress.completed:
                progress.progress_percentage = min(progress.progress_percentage + 10, 100)
                progress.last_accessed = timezone.now()
                progress.save()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_bookmark(request, resource_id):
    resource = get_object_or_404(LearningResource, id=resource_id, is_published=True)
    
    progress, _ = UserProgress.objects.get_or_create(
        user=request.user,
        resource=resource
    )
    progress.bookmarked = not progress.bookmarked
    progress.save()
    
    return Response({
        'bookmarked': progress.bookmarked,
        'message': 'Bookmark updated successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_quiz(request, resource_id):
    resource = get_object_or_404(LearningResource, id=resource_id, is_published=True)
    
    if resource.resource_type != 'quiz':
        return Response({'error': 'This resource is not a quiz'}, status=400)
    
    serializer = QuizSubmissionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    answers = serializer.validated_data['answers']
    time_spent = serializer.validated_data['time_spent']
    
    # Fetch all questions and options once
    questions = {q.id: q for q in resource.quiz_questions.all()}
    options = {o.id: o for o in QuizOption.objects.filter(question__resource=resource)}
    
    correct_answers = 0
    for answer in answers:
        question = questions.get(answer['question_id'])
        option = options.get(answer['option_id'])
        if question and option and option.is_correct:
            correct_answers += 1
    
    total_questions = len(questions)
    score = (correct_answers / total_questions) * 100 if total_questions else 0
    
    # Save quiz attempt
    quiz_attempt = UserQuizAttempt.objects.create(
        user=request.user,
        resource=resource,
        total_questions=total_questions,
        correct_answers=correct_answers,
        answers=answers
    )
    
    # Update user progress
    progress, _ = UserProgress.objects.get_or_create(user=request.user, resource=resource)
    progress.time_spent += time_spent
    progress.completed = True
    progress.progress_percentage = 100
    progress.save()
    
    return Response({
        'score': score,
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'attempt_id': quiz_attempt.id,
        'message': 'Quiz submitted successfully'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_progress(request):
    progress = UserProgress.objects.filter(user=request.user).select_related('resource')
    serializer = UserProgressSerializer(progress, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_quiz_history(request):
    attempts = UserQuizAttempt.objects.filter(user=request.user).select_related('resource')
    serializer = UserQuizAttemptSerializer(attempts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bookmarked_resources(request):
    progress = UserProgress.objects.filter(
        user=request.user,
        bookmarked=True,
        resource__is_published=True
    ).select_related('resource')
    
    resources = [p.resource for p in progress]
    serializer = LearningResourceSerializer(resources, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_resource_category(request):
    serializer = ResourceCategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Resource category created', 'data': serializer.data}, status=201)
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_learning_resource(request):
    serializer = LearningResourceSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Learning resource created', 'data': serializer.data}, status=201)
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_external_link(request, resource_id):
    resource = get_object_or_404(LearningResource, id=resource_id)
    serializer = ExternalLinkSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(resource=resource)
        return Response({'message': 'External link created', 'data': serializer.data}, status=201)
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_quiz_question(request, resource_id):
    resource = get_object_or_404(LearningResource, id=resource_id)
    serializer = QuizQuestionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(resource=resource)
        return Response({'message': 'Quiz question created', 'data': serializer.data}, status=201)
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_quiz_option(request, question_id):
    question = get_object_or_404(QuizQuestion, id=question_id)
    serializer = QuizOptionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(question=question)
        return Response({'message': 'Quiz option created', 'data': serializer.data}, status=201)
    return Response(serializer.errors, status=400)




# report 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_incident_report(request):
    serializer = IncidentReportCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        try:
            incident = serializer.save()
            
            # Auto-generate title if not provided
            if not incident.title:
                incident_type_display = dict(IncidentReport.INCIDENT_TYPES).get(incident.incident_type, 'Incident')
                incident.title = f"{incident_type_display} - {timezone.localtime(incident.incident_date).strftime('%b %d, %Y')}"
                incident.save()
            
            # Create initial status update
            IncidentUpdate.objects.create(
                incident=incident,
                status='submitted',
                message='Incident report submitted successfully.',
                created_by=request.user
            )
            
            full_serializer = IncidentReportSerializer(incident)
            return Response(full_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IncidentReportListView(ListAPIView):
    serializer_class = IncidentReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return IncidentReport.objects.filter(user=user).prefetch_related('media', 'updates').order_by('-created_at')

class IncidentReportDetailView(RetrieveAPIView):
    serializer_class = IncidentReportSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        return IncidentReport.objects.filter(user=user).prefetch_related('media', 'updates')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_incident_media(request, incident_id):
    try:
        incident = IncidentReport.objects.get(id=incident_id, user=request.user)
    except IncidentReport.DoesNotExist:
        return Response({'error': 'Incident report not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = MediaUploadSerializer(data=request.data)
    if serializer.is_valid():
        try:
            media = serializer.save(incident=incident)
            return Response({
                'message': 'Media uploaded successfully',
                'media_id': media.id
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def incident_statistics(request):
    user = request.user
    total_reports = IncidentReport.objects.filter(user=user).count()
    
    status_counts = {
        'submitted': IncidentReport.objects.filter(user=user, status='submitted').count(),
        'under_review': IncidentReport.objects.filter(user=user, status='under_review').count(),
        'resolved': IncidentReport.objects.filter(user=user, status='resolved').count(),
        'dismissed': IncidentReport.objects.filter(user=user, status='dismissed').count(),
    }
    
    type_counts = {
        incident_type: IncidentReport.objects.filter(
            user=user, incident_type=incident_type
        ).count()
        for incident_type, _ in IncidentReport.INCIDENT_TYPES
    }
    
    return Response({
        'total_reports': total_reports,
        'status_counts': status_counts,
        'type_counts': type_counts,
        'last_submission': IncidentReport.objects.filter(
            user=user
        ).order_by('-created_at').first().created_at if total_reports > 0 else None
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_incidents(request):
    incidents = IncidentReport.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    serializer = IncidentReportSerializer(incidents, many=True)
    return Response(serializer.data)