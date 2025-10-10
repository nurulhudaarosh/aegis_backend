from rest_framework import status,viewsets
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from datetime import timedelta
import json
import logging



from .models import (
    DeactivationAttempt,
    EmergencyAlert,
    EmergencyContact,
    EmergencyNotification,
    EmergencyResponse,
    ExternalLink,
    LocationUpdate,
    MediaCapture,
    ResourceCategory,
    LearningResource,
    SafetyCheckIn,
    SafetyCheckSettings,
    UserProgress,
    UserQuizAttempt,
    QuizQuestion,
    QuizOption,
    IncidentReport, 
    IncidentUpdate,
    VideoEvidence,
)

from .serializers import (
    DeactivationSerializer,
    EmergencyActivationSerializer,
    EmergencyAlertDetailSerializer,
    EmergencyAlertSerializer,
    EmergencyContactSerializer, 
    EmergencyContactCreateSerializer,
    EmergencyNotificationSerializer,
    EmergencyResponseSerializer,
    IncidentUpdateSerializer,
    LocationUpdateRequestSerializer,
    LocationUpdateSerializer,
    ManualCheckInSerializer,
    MediaCaptureSerializer,
    SafetyCheckInSerializer,
    SafetyCheckSettingsSerializer,
    SafetyStatisticsSerializer,
    TestAlertSerializer,
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
    VideoEvidenceCreateSerializer,
    VideoEvidenceSerializer,
    VideoEvidenceStatusSerializer,
    VideoEvidenceUpdateSerializer,
    VideoUploadSerializer,
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
        if self.request.user.is_authenticated and self.request.user.user_type == 'controller' :
            queryset = LearningResource.objects.all()
        else :
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
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'user_type', None) == 'controller':
            return LearningResource.objects.all()
        return LearningResource.objects.filter(is_published=True)
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
    if(request.user.user_type == 'controller') :
        resource = get_object_or_404(LearningResource, id=resource_id)
    else :
        resource = get_object_or_404(LearningResource, id=resource_id, is_published=True)

    if resource.resource_type != 'quiz':
        return Response({'error': 'This resource is not a quiz'}, status=400)
    
    serializer = QuizSubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        print("Validation errors:", serializer.errors)  
        return Response(serializer.errors, status=400)
    print('j')
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

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def toggle_visibility(request, resource_id):
    resource = get_object_or_404(LearningResource, id=resource_id)
    
    if resource.is_published :
        resource.is_published = False
    else :
        resource.is_published = True
    resource.save()
    
    return Response({
        'message': 'visibility updated successfully'
    })

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def learning_resource_delete(request, id):
    resource = get_object_or_404(LearningResource, id=id)

    if request.user.user_type != 'controller':
        return Response({'detail': 'Not authorized to delete this resource.'}, status=403)

    resource.delete()
    return Response({'message': 'Deleted successfully'}, status=204)



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


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_learning_resource(request, resource_id):
    try:
        resource = get_object_or_404(LearningResource, id=resource_id)
        
        # Check if user has permission to update (you can add more specific permissions)
        # For example, only allow authors or admins to update
        
        serializer = LearningResourceSerializer(
            resource, 
            data=request.data, 
            partial=True,  # Allow partial updates
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Resource updated successfully',
                'data': serializer.data
            }, status=200)
        
        return Response(serializer.errors, status=400)
        
    except LearningResource.DoesNotExist:
        return Response({'error': 'Resource not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_quiz_question(request, question_id):
    try:
        question = get_object_or_404(QuizQuestion, id=question_id)
        
        serializer = QuizQuestionSerializer(
            question, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Question updated successfully',
                'data': serializer.data
            }, status=200)
        
        return Response(serializer.errors, status=400)
        
    except QuizQuestion.DoesNotExist:
        return Response({'error': 'Question not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_quiz_option(request, option_id):

    try:
        option = get_object_or_404(QuizOption, id=option_id)
        
        serializer = QuizOptionSerializer(
            option, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Option updated successfully',
                'data': serializer.data
            }, status=200)
        
        return Response(serializer.errors, status=400)
        
    except QuizOption.DoesNotExist:
        return Response({'error': 'Option not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_resource_category(request, category_id):
    try:
        category = get_object_or_404(ResourceCategory, id=category_id)
        
        serializer = ResourceCategorySerializer(
            category, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Category updated successfully',
                'data': serializer.data
            }, status=200)
        
        return Response(serializer.errors, status=400)
        
    except ResourceCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_external_link(request, link_id):
    try:
        link = get_object_or_404(ExternalLink, id=link_id)
        
        serializer = ExternalLinkSerializer(
            link, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'External link updated successfully',
                'data': serializer.data
            }, status=200)
        
        return Response(serializer.errors, status=400)
        
    except ExternalLink.DoesNotExist:
        return Response({'error': 'External link not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_quiz_question(request, question_id):

    try:
        question = get_object_or_404(QuizQuestion, id=question_id)
        question.delete()
        return Response({'message': 'Question deleted successfully'}, status=200)
    except QuizQuestion.DoesNotExist:
        return Response({'error': 'Question not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_quiz_option(request, option_id):
    try:
        option = get_object_or_404(QuizOption, id=option_id)
        option.delete()
        return Response({'message': 'Option deleted successfully'}, status=200)
    except QuizOption.DoesNotExist:
        return Response({'error': 'Option not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_resource_category(request, category_id):

    try:
        category = get_object_or_404(ResourceCategory, id=category_id)
        category.delete()
        return Response({'message': 'Category deleted successfully'}, status=200)
    except ResourceCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_external_link(request, link_id):

    try:
        link = get_object_or_404(ExternalLink, id=link_id)
        link.delete()
        return Response({'message': 'External link deleted successfully'}, status=200)
    except ExternalLink.DoesNotExist:
        return Response({'error': 'External link not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


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
        return IncidentReport.objects.all().prefetch_related('media', 'updates').order_by('-created_at')

class IncidentReportDetailView(RetrieveAPIView):
    serializer_class = IncidentReportSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return IncidentReport.objects.all().prefetch_related('media', 'updates')

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

    total_reports = IncidentReport.objects.all().count()
    
    status_counts = {
        'submitted': IncidentReport.objects.filter(status='submitted').count(),
        'under_review': IncidentReport.objects.filter(status='under_review').count(),
        'resolved': IncidentReport.objects.filter(status='resolved').count(),
        'dismissed': IncidentReport.objects.filter(status='dismissed').count(),
    }
    
    type_counts = {
        incident_type: IncidentReport.objects.filter(
            incident_type=incident_type
        ).count()
        for incident_type, _ in IncidentReport.INCIDENT_TYPES
    }
    
    return Response({
        'total_reports': total_reports,
        'status_counts': status_counts,
        'type_counts': type_counts,
        'last_submission': IncidentReport.objects.filter(
        ).order_by('-created_at').first().created_at if total_reports > 0 else None
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_incidents(request):
    incidents = IncidentReport.objects.all().order_by('-created_at')[:5]
    
    serializer = IncidentReportSerializer(incidents, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_incident_status(request, incident_id):
    try:
        incidentReport = IncidentReport.objects.get(id=incident_id)
    except IncidentReport.DoesNotExist:
        return Response({'error': 'Incident report not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = IncidentUpdateSerializer(
        data=request.data,
        context={'request': request, 'incident': incidentReport}
    )

    if serializer.is_valid():
        update = serializer.save(
            incident=incidentReport
        )
        # Update incident status
        incidentReport.status = serializer.validated_data['status']
        if 'priority' in request.data:
            print(request.data)
            incidentReport.priority = request.data['priority']
        incidentReport.save()
        return Response(IncidentUpdateSerializer(update).data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# safety check

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def safety_settings(request):
    try:
        settings = SafetyCheckSettings.objects.get(user=request.user)
    except SafetyCheckSettings.DoesNotExist:
        settings = SafetyCheckSettings.objects.create(user=request.user)

    if request.method == 'GET':
        serializer = SafetyCheckSettingsSerializer(settings)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = SafetyCheckSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_check_in(request):
    serializer = ManualCheckInSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create a check-in record
    check_in = SafetyCheckIn.objects.create(
        user=request.user,
        status='safe',
        scheduled_at=timezone.now(),
        responded_at=timezone.now(),
        location_lat=serializer.validated_data.get('location_lat'),
        location_lng=serializer.validated_data.get('location_lng'),
        notes=serializer.validated_data.get('notes', '')
    )

    # Schedule next check-in based on user settings
    try:
        settings = SafetyCheckSettings.objects.get(user=request.user)
        if settings.is_enabled:
            next_check_in = timezone.now() + timedelta(minutes=settings.check_in_frequency)
            SafetyCheckIn.objects.create(
                user=request.user,
                status='pending',
                scheduled_at=next_check_in
            )
    except SafetyCheckSettings.DoesNotExist:
        pass

    return Response({
        'message': 'Safety check-in recorded successfully',
        'check_in': SafetyCheckInSerializer(check_in).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_emergency_alert_demo(request):
    serializer = TestAlertSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create test alert
    # alert = EmergencyAlert.objects.create(
    #     user=request.user,
    #     alert_type='test',
    #     message=serializer.validated_data['message']
    # )

    # Here you would integrate with your notification service (Twilio, Firebase, etc.)
    # For now, we'll just return success
    print('alert success')

    return Response({
        'message': 'Test emergency alert sent successfully',
        # 'alert': EmergencyAlertSerializer(alert).data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def safety_statistics(request):
    # Calculate statistics for the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)

    total_check_ins = SafetyCheckIn.objects.filter(
        user=request.user,
        created_at__gte=thirty_days_ago
    ).count()

    successful_check_ins = SafetyCheckIn.objects.filter(
        user=request.user,
        status='safe',
        created_at__gte=thirty_days_ago
    ).count()

    missed_check_ins = SafetyCheckIn.objects.filter(
        user=request.user,
        status='missed',
        created_at__gte=thirty_days_ago
    ).count()

    emergency_alerts = EmergencyAlert.objects.filter(
        user=request.user,
        created_at__gte=thirty_days_ago
    ).count()

    response_rate = (successful_check_ins / total_check_ins * 100) if total_check_ins > 0 else 100

    last_check_in = SafetyCheckIn.objects.filter(
        user=request.user,
        status='safe'
    ).order_by('-responded_at').first()

    next_check_in = SafetyCheckIn.objects.filter(
        user=request.user,
        status='pending'
    ).order_by('scheduled_at').first()

    statistics = {
        'total_check_ins': total_check_ins,
        'successful_check_ins': successful_check_ins,
        'missed_check_ins': missed_check_ins,
        'emergency_alerts': emergency_alerts,
        'response_rate': round(response_rate, 1),
        'last_check_in': last_check_in.responded_at if last_check_in else None,
        'next_check_in': next_check_in.scheduled_at if next_check_in else None
    }

    serializer = SafetyStatisticsSerializer(statistics)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_in_history(request):
    check_ins = SafetyCheckIn.objects.filter(user=request.user).order_by('-scheduled_at')[:20]
    serializer = SafetyCheckInSerializer(check_ins, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alert_history(request):
    alerts = EmergencyAlert.objects.filter(user=request.user).order_by('-created_at')[:20]
    serializer = EmergencyAlertSerializer(alerts, many=True)
    return Response(serializer.data)


# silent capture 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_video_evidence(request):

    serializer = VideoEvidenceCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        evidence = VideoEvidence.objects.create(
            user=request.user,
            **serializer.validated_data
        )
        
        full_serializer = VideoEvidenceSerializer(evidence, context={'request': request})
        return Response({
            'message': 'Video evidence record created successfully',
            'evidence': full_serializer.data,
            'evidence_id': evidence.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to create evidence record: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_video_file(request, evidence_id):
    
    try:
        evidence = VideoEvidence.objects.get(id=evidence_id, user=request.user)
    except VideoEvidence.DoesNotExist:
        return Response(
            {'error': 'Video evidence record not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if evidence.video_file:
        return Response(
            {'error': 'Video file already uploaded for this evidence'},
            status=status.HTTP_400_BAD_REQUEST
        )

    file_serializer = VideoUploadSerializer(data=request.data)
    if not file_serializer.is_valid():
        return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        evidence.video_file = file_serializer.validated_data['video_file']
        evidence.file_size = evidence.video_file.size
        evidence.save()
        
        full_serializer = VideoEvidenceSerializer(evidence, context={'request': request})
        return Response({
            'message': 'Video file uploaded successfully',
            'evidence': full_serializer.data
        })
        
    except Exception as e:
        if evidence.video_file:
            try:
                evidence.video_file.delete(save=False)
            except:
                pass
        return Response(
            {'error': f'Failed to upload video file: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_video_evidence(request):
    
    if request.user.user_type == 'controller':
        evidence = VideoEvidence.objects.all().order_by('-recorded_at')
    else:
        evidence = VideoEvidence.objects.filter(user=request.user).order_by('-recorded_at')
    
    # Filtering options
    status_filter = request.query_params.get('status')
    if status_filter:
        evidence = evidence.filter(status=status_filter)
    
    type_filter = request.query_params.get('type')
    if type_filter:
        evidence = evidence.filter(type=type_filter)
    
    is_anonymous = request.query_params.get('is_anonymous')
    if is_anonymous is not None:
        evidence = evidence.filter(is_anonymous=is_anonymous.lower() == 'true')
    
    date_from = request.query_params.get('date_from')
    if date_from:
        evidence = evidence.filter(recorded_at__date__gte=date_from)
    
    date_to = request.query_params.get('date_to')
    if date_to:
        evidence = evidence.filter(recorded_at__date__lte=date_to)
    
    serializer = VideoEvidenceSerializer(evidence, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_video_evidence(request, evidence_id):
    
    try:
        evidence = VideoEvidence.objects.get(id=evidence_id)
        # if not evidence.user_can_access(request.user):
        #     return Response(
        #         {'error': 'Access denied'},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        serializer = VideoEvidenceSerializer(evidence, context={'request': request})
        return Response(serializer.data)
    except VideoEvidence.DoesNotExist:
        return Response(
            {'error': 'Video evidence not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_video_evidence(request, evidence_id):
    
    try:
        evidence = VideoEvidence.objects.get(id=evidence_id)
        # if not evidence.user_can_modify(request.user):
        #     return Response(
        #         {'error': 'You can only edit your own evidence'},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
    except VideoEvidence.DoesNotExist:
        return Response(
            {'error': 'Video evidence not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = VideoEvidenceUpdateSerializer(
        evidence, 
        data=request.data, 
        partial=request.method == 'PATCH'
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        serializer.save()
        full_serializer = VideoEvidenceSerializer(evidence, context={'request': request})
        return Response({
            'message': 'Video evidence updated successfully',
            'evidence': full_serializer.data
        })
    except Exception as e:
        return Response(
            {'error': f'Failed to update evidence: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_evidence_status(request, evidence_id):
    
    if request.user.user_type != 'controller':
        return Response(
            {'error': 'Only controllers can update evidence status'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        evidence = VideoEvidence.objects.get(id=evidence_id)
    except VideoEvidence.DoesNotExist:
        return Response(
            {'error': 'Video evidence not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = VideoEvidenceStatusSerializer(evidence, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        serializer.save()
        full_serializer = VideoEvidenceSerializer(evidence, context={'request': request})
        return Response({
            'message': 'Evidence status updated successfully',
            'evidence': full_serializer.data
        })
    except Exception as e:
        return Response(
            {'error': f'Failed to update status: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_video_evidence(request, evidence_id):

    try:
        evidence = VideoEvidence.objects.get(id=evidence_id)
        
        if evidence.video_file:
            evidence.video_file.delete(save=False)
        
        evidence.delete()
        
        return Response({
            'message': 'Video evidence deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
        
    except VideoEvidence.DoesNotExist:
        return Response(
            {'error': 'Video evidence not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def video_evidence_statistics(request):

    if request.user.user_type == 'controller':
        user_evidence = VideoEvidence.objects.all()
    else:
        user_evidence = VideoEvidence.objects.filter(user=request.user)
    
    total_videos = user_evidence.count()
    total_duration = sum(evidence.duration_seconds for evidence in user_evidence)
    total_file_size = sum(evidence.file_size for evidence in user_evidence)
    anonymous_count = user_evidence.filter(is_anonymous=True).count()
    
    # Status statistics
    status_stats = {
        status: user_evidence.filter(status=status).count()
        for status, _ in VideoEvidence.STATUS_CHOICES
    }
    
    # Type statistics
    type_stats = {
        evidence_type: user_evidence.filter(type=evidence_type).count()
        for evidence_type, _ in VideoEvidence.EVIDENCE_TYPE
    }
    
    # Recent activity (last 7 days)
    week_ago = timezone.now() - timezone.timedelta(days=7)
    recent_count = user_evidence.filter(created_at__gte=week_ago).count()
    
    return Response({
        'total_videos': total_videos,
        'total_duration_seconds': total_duration,
        'total_duration_display': f"{total_duration // 3600}h {(total_duration % 3600) // 60}m",
        'total_file_size': total_file_size,
        'total_file_size_display': f"{total_file_size / (1024 * 1024 * 1024):.2f} GB",
        'anonymous_count': anonymous_count,
        'recent_count': recent_count,
        'average_duration_seconds': total_duration / total_videos if total_videos > 0 else 0,
        'status_statistics': status_stats,
        'type_statistics': type_stats,
    })



# emergecy alert 



logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def activate_emergency(request):
    """
    Activate emergency panic mode
    POST /api/aegis/emergency/activate/
    {
        "activation_method": "button",
        "latitude": 23.8103,
        "longitude": 90.4125,
        "address": "Dhaka, Bangladesh",
        "is_silent": false,
        "emergency_type": "medical",
        "description": "Need immediate medical assistance"
    }
    """
    serializer = EmergencyActivationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            with transaction.atomic():
                # Create emergency alert
                alert = EmergencyAlert.objects.create(
                    user=request.user,
                    activation_method=serializer.validated_data['activation_method'],
                    initial_latitude=serializer.validated_data.get('latitude'),
                    initial_longitude=serializer.validated_data.get('longitude'),
                    initial_address=serializer.validated_data.get('address', ''),
                    is_silent=serializer.validated_data['is_silent'],
                    emergency_type=serializer.validated_data.get('emergency_type', 'general'),
                    description=serializer.validated_data.get('description', '')
                )
                
                # Record initial location
                if serializer.validated_data.get('latitude') and serializer.validated_data.get('longitude'):
                    LocationUpdate.objects.create(
                        alert=alert,
                        latitude=serializer.validated_data['latitude'],
                        longitude=serializer.validated_data['longitude'],
                        accuracy=serializer.validated_data.get('accuracy'),
                        speed=serializer.validated_data.get('speed')
                    )
                
                # Find and assign nearby responders
                assigned_responders = assign_nearby_responders(alert)
                
                # Notify emergency contacts
                notified_contacts = notify_emergency_contacts(alert)
                
                # Create notification for user
                EmergencyNotification.objects.create(
                    user=request.user,
                    alert=alert,
                    notification_type='alert_activated',
                    title='Emergency Alert Activated',
                    message=f'Emergency alert {alert.alert_id} has been activated. {len(assigned_responders)} responders notified.',
                    data={
                        'responders_count': len(assigned_responders),
                        'contacts_notified': notified_contacts,
                        'alert_id': alert.alert_id
                    }
                )
                
                logger.info(f"Emergency activated: {alert.alert_id} by user {request.user.email}")

            return Response({
                'success': True,
                'alert_id': alert.alert_id,
                'message': 'Emergency activated successfully',
                'responders_assigned': len(assigned_responders),
                'contacts_notified': notified_contacts,
                'fake_screen_active': alert.fake_screen_active,
                'activated_at': alert.activated_at.isoformat()
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error activating emergency: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to activate emergency. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def deactivate_emergency(request):
    """
    Deactivate emergency with PIN verification
    POST /api/aegis/emergency/deactivate/
    {
        "pin": "2580",
        "alert_id": "EMG-ABC12345"
    }
    """
    serializer = DeactivationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            alert_id = serializer.validated_data['alert_id']
            pin = serializer.validated_data['pin']
            
            alert = get_object_or_404(EmergencyAlert, alert_id=alert_id, user=request.user)
            
            # Check if alert is already cancelled/resolved
            if alert.status in ['cancelled', 'resolved']:
                return Response({
                    'success': False,
                    'error': 'Emergency alert has already been deactivated.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Record deactivation attempt
            attempt = DeactivationAttempt.objects.create(
                alert=alert,
                attempted_pin=pin,
                device_info={
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': get_client_ip(request)
                },
                location_at_attempt={
                    'latitude': float(alert.initial_latitude) if alert.initial_latitude else None,
                    'longitude': float(alert.initial_longitude) if alert.initial_longitude else None
                }
            )
            
            # Verify PIN (using the hardcoded PIN from frontend - in production, use user profile)
            if pin == "2580":  # TODO: Get from user profile in production
                alert.status = 'cancelled'
                alert.cancelled_at = timezone.now()
                alert.fake_screen_active = False
                alert.save()
                
                attempt.is_successful = True
                attempt.save()
                
                # Notify responders about cancellation
                notify_responders_cancellation(alert)
                
                # Create notification
                EmergencyNotification.objects.create(
                    user=request.user,
                    alert=alert,
                    notification_type='alert_resolved',
                    title='Emergency Cancelled',
                    message=f'Emergency alert {alert.alert_id} has been successfully cancelled.',
                    data={
                        'cancelled_at': alert.cancelled_at.isoformat(),
                        'alert_id': alert.alert_id
                    }
                )
                
                logger.info(f"Emergency deactivated: {alert.alert_id} by user {request.user.email}")
                
                return Response({
                    'success': True,
                    'message': 'Emergency deactivated successfully',
                    'alert_status': alert.status,
                    'cancelled_at': alert.cancelled_at.isoformat()
                })
            else:
                # Incorrect PIN
                alert.deactivation_attempts += 1
                alert.save()
                
                attempts = alert.deactivation_attempts
                
                # Handle suspicious activity after multiple attempts
                if attempts >= 3:
                    handle_suspicious_deactivation(alert, attempts)
                
                logger.warning(f"Failed deactivation attempt {attempts} for alert {alert.alert_id}")
                
                return Response({
                    'success': False,
                    'message': 'Incorrect PIN. Emergency remains active.',
                    'attempts': attempts,
                    'fake_screen_active': True  # Keep fake screen active
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except EmergencyAlert.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Emergency alert not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def update_location(request):
    """
    Update victim's location during emergency
    POST /api/aegis/emergency/update-location/
    {
        "alert_id": "EMG-ABC12345",
        "latitude": 23.8105,
        "longitude": 90.4127,
        "accuracy": 15.5,
        "speed": 2.5,
        "altitude": 10.0,
        "heading": 45.0
    }
    """
    print('update location called')
    serializer = LocationUpdateRequestSerializer(data=request.data)
    if serializer.is_valid():
        try:
            alert = get_object_or_404(EmergencyAlert, alert_id=serializer.validated_data['alert_id'], user=request.user)
            
            # Check if alert is active
            if alert.status != 'active':
                return Response({
                    'success': False,
                    'error': 'Cannot update location for inactive emergency'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            location_update = LocationUpdate.objects.create(
                alert=alert,
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude'],
                accuracy=serializer.validated_data.get('accuracy'),
                speed=serializer.validated_data.get('speed'),
                altitude=serializer.validated_data.get('altitude'),
                heading=serializer.validated_data.get('heading')
            )
            
            # Notify responders about location update
            notify_responders_location_update(alert, location_update)
            
            logger.info(f"Location updated for alert {alert.alert_id}")
            
            return Response({
                'success': True,
                'message': 'Location updated successfully',
                'timestamp': location_update.timestamp.isoformat()
            })
            
        except EmergencyAlert.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Emergency alert not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_media(request):
    """
    Upload media captured during emergency
    POST /api/aegis/emergency/upload-media/
    FormData:
    - alert_id: "EMG-ABC12345"
    - media_type: "audio" | "photo" | "video"
    - file: [file]
    - duration: 30 (optional, for audio/video)
    """
    print('upload media called')
    serializer = MediaUploadSerializer(data=request.data)
    if serializer.is_valid():
        try:
            alert = get_object_or_404(EmergencyAlert, alert_id=serializer.validated_data['alert_id'], user=request.user)
            
            # Check if alert is active
            if alert.status != 'active':
                return Response({
                    'success': False,
                    'error': 'Cannot upload media for inactive emergency'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            media_file = request.FILES['file']
            
            # Generate secure file path
            file_extension = media_file.name.split('.')[-1]
            secure_filename = f"{alert.alert_id}_{int(timezone.now().timestamp())}.{file_extension}"
            
            # In production, upload to secure storage (S3, etc.)
            # For now, we'll create a record with a mock URL
            media_capture = MediaCapture.objects.create(
                alert=alert,
                media_type=serializer.validated_data['media_type'],
                file=media_file,
                file_size=media_file.size,
                duration=serializer.validated_data.get('duration'),
                mime_type=media_file.content_type,
                # In production, you would encrypt the file and store the key
                is_encrypted=True,
                encryption_key="encrypted_key_placeholder"  
            )
            
            # Notify responders about new media
            notify_responders_media_upload(alert, media_capture)
            
            # Create notification
            EmergencyNotification.objects.create(
                user=request.user,
                alert=alert,
                notification_type='media_uploaded',
                title='Media Captured',
                message=f'New {media_capture.media_type} captured and uploaded.',
                data={
                    'media_type': media_capture.media_type,
                    'file_size': media_capture.file_size,
                    'captured_at': media_capture.captured_at.isoformat()
                }
            )
            
            logger.info(f"Media uploaded for alert {alert.alert_id}: {media_capture.media_type}")
            
            return Response({
                'success': True,
                'media_id': media_capture.id,
                'media_type': media_capture.media_type,
                'file_size': media_capture.file_size,
                'message': 'Media uploaded successfully'
            })
            
        except EmergencyAlert.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Emergency alert not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emergency_details(request, alert_id):
    """
    Get detailed emergency information
    GET /api/aegis/emergency/EMG-ABC12345/
    """
    try:
        alert = get_object_or_404(EmergencyAlert, alert_id=alert_id, user=request.user)
        serializer = EmergencyAlertDetailSerializer(alert)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except EmergencyAlert.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Emergency alert not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_emergencies(request):
    """
    Get user's active emergencies
    GET /api/aegis/emergency/active/
    """
    alerts = EmergencyAlert.objects.filter(user=request.user, status='active').order_by('-activated_at')
    serializer = EmergencyAlertSerializer(alerts, many=True)
    
    return Response({
        'success': True,
        'count': alerts.count(),
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emergency_history(request):
    """
    Get user's emergency history
    GET /api/aegis/emergency/history/
    """
    alerts = EmergencyAlert.objects.filter(user=request.user).exclude(status='active').order_by('-activated_at')
    serializer = EmergencyAlertSerializer(alerts, many=True)
    
    return Response({
        'success': True,
        'count': alerts.count(),
        'data': serializer.data
    })




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_responder_assignments(request):

    if request.user.user_type != 'agent':
        return Response({
            'success': False,
            'error': 'Only agents can access responder assignments'
        }, status=status.HTTP_403_FORBIDDEN)
    
    responses = EmergencyResponse.objects.filter(
        responder=request.user,
        alert__status='active'
    ).select_related('alert', 'alert__user').order_by('-notified_at')
    
    serializer = EmergencyResponseSerializer(responses, many=True)
    
    return Response({
        'success': True,
        'count': responses.count(),
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def update_response_status(request):
    """
    Update responder's status for an emergency
    POST /api/aegis/responder/update-status/
    {
        "response_id": 1,
        "status": "en_route",
        "notes": "On my way to location",
        "eta_minutes": 5
    }
    """
    if request.user.user_type != 'agent':
        return Response({
            'success': False,
            'error': 'Only agents can update response status'
        }, status=status.HTTP_403_FORBIDDEN)
    
    response_id = request.data.get('response_id')
    new_status = request.data.get('status')
    
    if not response_id or not new_status:
        return Response({
            'success': False,
            'error': 'response_id and status are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        response = EmergencyResponse.objects.get(id=response_id, responder=request.user)
        
        # Validate status transition
        valid_transitions = {
            'notified': ['dispatched', 'cancelled'],
            'dispatched': ['en_route', 'cancelled'],
            'en_route': ['on_scene', 'cancelled'],
            'on_scene': ['completed', 'cancelled'],
            'completed': [],
            'cancelled': []
        }
        
        current_status = response.status
        if new_status not in valid_transitions.get(current_status, []):
            return Response({
                'success': False,
                'error': f'Invalid status transition from {current_status} to {new_status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        response.status = new_status
        response.notes = request.data.get('notes', response.notes)
        response.eta_minutes = request.data.get('eta_minutes', response.eta_minutes)
        
        # Update timestamps based on status
        now = timezone.now()
        if new_status == 'dispatched' and not response.dispatched_at:
            response.dispatched_at = now
        elif new_status == 'en_route' and not response.dispatched_at:
            response.dispatched_at = now
        elif new_status == 'on_scene' and not response.arrived_at:
            response.arrived_at = now
        elif new_status == 'completed' and not response.completed_at:
            response.completed_at = now
        elif new_status == 'cancelled':
            response.completed_at = now
        
        response.save()
        
        # Notify user about status update
        EmergencyNotification.objects.create(
            user=response.alert.user,
            alert=response.alert,
            notification_type='status_update',
            title='Responder Status Update',
            message=f'Responder {request.user.full_name} is now {new_status.replace("_", " ").title()}',
            data={
                'responder_status': new_status,
                'responder_name': request.user.full_name,
                'eta_minutes': response.eta_minutes,
                'updated_at': now.isoformat()
            }
        )
        
        # If response is completed, check if all responses are completed
        if new_status == 'completed':
            check_emergency_completion(response.alert)
        
        logger.info(f"Responder {request.user.email} updated status to {new_status} for alert {response.alert.alert_id}")
        
        return Response({
            'success': True,
            'message': 'Status updated successfully',
            'response_status': response.status,
            'updated_at': now.isoformat()
        })
        
    except EmergencyResponse.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Response assignment not found'
        }, status=status.HTTP_404_NOT_FOUND)



def assign_nearby_responders(alert):
    """
    Find and assign nearby responders based on location
    """
    if not alert.initial_latitude or not alert.initial_longitude:
        # If no location, assign any available responders
        available_responders = User.objects.filter(
            user_type='agent',
            status='available'
        )[:3]
    else:
        # Find available responders (simplified - in production use geospatial queries)
        available_responders = User.objects.filter(
            user_type='agent',
            status='available',
            latitude__isnull=False,
            longitude__isnull=False
        )[:3]
    
    assigned = []
    for i, responder in enumerate(available_responders):
        # Calculate ETA based on distance (simplified)
        eta = calculate_eta(alert, responder, i)
        
        try:
            response = EmergencyResponse.objects.create(
                alert=alert,
                responder=responder,
                eta_minutes=eta,
                status='notified'
            )
            assigned.append(responder)
            
            # Update responder status
            responder.status = 'busy'
            responder.save()
            
            # Notify responder
            EmergencyNotification.objects.create(
                user=responder,
                alert=alert,
                notification_type='responder_assigned',
                title='New Emergency Assignment',
                message=f'You have been assigned to emergency {alert.alert_id}. Estimated arrival: {eta} minutes',
                data={
                    'alert_id': alert.alert_id,
                    'eta_minutes': eta,
                    'user_name': alert.user.full_name,
                    'emergency_type': alert.emergency_type,
                    'location': alert.initial_address
                }
            )
            
            logger.info(f"Assigned responder {responder.email} to alert {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Error assigning responder {responder.email}: {str(e)}")
    
    return assigned


def notify_emergency_contacts(alert):
    """
    Notify user's emergency contacts using the existing model
    """
    contacts = EmergencyContact.objects.filter(
        user=alert.user, 
        is_emergency_contact=True
    )
    
    notified_count = 0
    for contact in contacts:
        try:
            # In production, implement actual SMS/email sending
            send_emergency_notification(contact, alert)
            notified_count += 1
            
            logger.info(f"Notified emergency contact: {contact.name} ({contact.phone})")
            
        except Exception as e:
            logger.error(f"Failed to notify {contact.name}: {str(e)}")
    
    return notified_count


def send_emergency_notification(contact, alert):
    """
    Send emergency notification to contact
    """
    # SMS message template
    message = f"""
🚨 EMERGENCY ALERT 🚨

{alert.user.full_name} has activated an emergency alert.

Alert ID: {alert.alert_id}
Time: {alert.activated_at.strftime('%Y-%m-%d %H:%M:%S')}
Location: {alert.initial_address or 'Location being tracked'}
Emergency Type: {alert.emergency_type.title()}

Please check the Aegis app for real-time updates.

Stay safe,
Aegis Emergency Response System
    """
    
    # TODO: Integrate with SMS service (Twilio, etc.)
    # TODO: Integrate with email service if contact has email
    print(f"SENDING SMS to {contact.phone}: {message}")
    
    return True


def notify_responders_cancellation(alert):
    """
    Notify responders about emergency cancellation
    """
    for response in alert.responses.all():
        response.status = 'cancelled'
        response.completed_at = timezone.now()
        response.save()
        
        # Update responder status back to available
        responder = response.responder
        responder.status = 'available'
        responder.save()
        
        EmergencyNotification.objects.create(
            user=response.responder,
            alert=alert,
            notification_type='alert_resolved',
            title='Emergency Cancelled',
            message=f'Emergency {alert.alert_id} has been cancelled by the user.',
            data={
                'cancelled_at': alert.cancelled_at.isoformat(),
                'alert_id': alert.alert_id
            }
        )


def notify_responders_location_update(alert, location_update):
    """
    Notify responders about location update
    """
    for response in alert.responses.all():
        EmergencyNotification.objects.create(
            user=response.responder,
            alert=alert,
            notification_type='location_update',
            title='Location Updated',
            message=f'Updated location received for emergency {alert.alert_id}',
            data={
                'alert_id': alert.alert_id,
                'latitude': float(location_update.latitude),
                'longitude': float(location_update.longitude),
                'timestamp': location_update.timestamp.isoformat(),
                'accuracy': location_update.accuracy
            }
        )


def notify_responders_media_upload(alert, media_capture):
    """
    Notify responders about new media upload
    """
    for response in alert.responses.all():
        EmergencyNotification.objects.create(
            user=response.responder,
            alert=alert,
            notification_type='media_uploaded',
            title='New Media Uploaded',
            message=f'New {media_capture.media_type} uploaded for emergency {alert.alert_id}',
            data={
                'media_type': media_capture.media_type,
                'media_id': media_capture.id,
                'file_size': media_capture.file_size,
                'captured_at': media_capture.captured_at.isoformat()
            }
        )


def handle_suspicious_deactivation(alert, attempts):
    """
    Handle multiple failed deactivation attempts
    """
    # Log security event
    logger.warning(f"SECURITY ALERT: Multiple failed deactivation attempts ({attempts}) for alert {alert.alert_id}")
    
    # Notify administrators
    admins = User.objects.filter(user_type='admin')
    for admin in admins:
        EmergencyNotification.objects.create(
            user=admin,
            alert=alert,
            notification_type='alert_activated',
            title='Suspicious Deactivation Attempts',
            message=f'Multiple failed deactivation attempts ({attempts}) for alert {alert.alert_id}. Possible coercion situation.',
            data={
                'attempts': attempts, 
                'alert_id': alert.alert_id,
                'user_email': alert.user.email,
                'user_name': alert.user.full_name
            }
        )


def check_emergency_completion(alert):
    """
    Check if all responses are completed and update alert status accordingly
    """
    active_responses = alert.responses.exclude(status__in=['completed', 'cancelled'])
    if not active_responses.exists():
        alert.status = 'resolved'
        alert.resolved_at = timezone.now()
        alert.save()
        
        # Notify user
        EmergencyNotification.objects.create(
            user=alert.user,
            alert=alert,
            notification_type='alert_resolved',
            title='Emergency Resolved',
            message=f'Emergency {alert.alert_id} has been successfully resolved.',
            data={
                'resolved_at': alert.resolved_at.isoformat(),
                'alert_id': alert.alert_id
            }
        )


def calculate_eta(alert, responder, index):
    """
    Calculate estimated time of arrival (simplified version)
    """
    # Mock ETA calculation - in production, use actual distance and traffic data
    base_eta = 3  # Base 3 minutes
    variation = (index * 2)  # Add variation based on responder order
    return base_eta + variation


def get_client_ip(request):
    """
    Get client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_notifications(request):
    """
    Get user's notifications
    GET /api/aegis/notifications/
    """
    notifications = EmergencyNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]  # Last 50 notifications
    
    unread_count = notifications.filter(is_read=False).count()
    
    serializer = EmergencyNotificationSerializer(notifications, many=True)
    
    return Response({
        'success': True,
        'unread_count': unread_count,
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """
    Mark notification as read
    POST /api/aegis/notifications/{id}/read/
    """
    try:
        notification = get_object_or_404(EmergencyNotification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        
        return Response({
            'success': True,
            'message': 'Notification marked as read'
        })
    except EmergencyNotification.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Notification not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def emergency_statistics(request):
    """
    Get user's emergency statistics
    GET /api/aegis/emergency/statistics/
    """
    user = request.user
    
    total_alerts = EmergencyAlert.objects.filter(user=user).count()
    active_alerts = EmergencyAlert.objects.filter(user=user, status='active').count()
    resolved_alerts = EmergencyAlert.objects.filter(user=user, status='resolved').count()
    cancelled_alerts = EmergencyAlert.objects.filter(user=user, status='cancelled').count()
    
    # Average response time (simplified)
    resolved_with_response = EmergencyAlert.objects.filter(
        user=user, 
        status='resolved',
        responses__isnull=False
    )
    
    avg_response_time = None
    if resolved_with_response.exists():
        # Mock average response time calculation
        avg_response_time = 8.5  # minutes
    
    return Response({
        'success': True,
        'data': {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'resolved_alerts': resolved_alerts,
            'cancelled_alerts': cancelled_alerts,
            'avg_response_time': avg_response_time,
            'emergency_contacts_count': EmergencyContact.objects.filter(user=user, is_emergency_contact=True).count()
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_emergency_updates(request, alert_id):
    """
    Get real-time updates for emergency - POLLING ENDPOINT
    GET /api/aegis/emergency/updates/EMG-ABC12345/
    """
    try:
        alert = get_object_or_404(EmergencyAlert, alert_id=alert_id, user=request.user)
        
        # Get latest data
        location_updates = LocationUpdate.objects.filter(alert=alert).order_by('-timestamp')[:5]
        media_captures = MediaCapture.objects.filter(alert=alert).order_by('-captured_at')[:10]
        responses = EmergencyResponse.objects.filter(alert=alert).select_related('responder')

        # Get and mark unread notifications safely
        unread_notifications = EmergencyNotification.objects.filter(alert=alert, is_read=False).order_by('-created_at')[:10]
        notification_serializer = EmergencyNotificationSerializer(unread_notifications, many=True)

        # ✅ Properly mark only these 10 as read
        ids = [n.id for n in unread_notifications]
        EmergencyNotification.objects.filter(id__in=ids).update(is_read=True)

        # Serialize the rest
        location_serializer = LocationUpdateSerializer(location_updates, many=True)
        media_serializer = MediaCaptureSerializer(media_captures, many=True)
        response_serializer = EmergencyResponseSerializer(responses, many=True)
        
        return Response({
            'success': True,
            'data': {
                'alert': EmergencyAlertSerializer(alert).data,
                'location_updates': location_serializer.data,
                'media_captures': media_serializer.data,
                'responses': response_serializer.data,
                'notifications': notification_serializer.data,
                'timestamp': timezone.now().isoformat()
            }
        })
        
    except EmergencyAlert.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Emergency alert not found'
        }, status=status.HTTP_404_NOT_FOUND)
