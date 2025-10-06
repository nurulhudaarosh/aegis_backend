from rest_framework import status,viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from datetime import timedelta



from .models import (
    EmergencyAlert,
    EmergencyContact,
    ExternalLink,
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
    EmergencyAlertSerializer,
    EmergencyContactSerializer, 
    EmergencyContactCreateSerializer,
    IncidentUpdateSerializer,
    ManualCheckInSerializer,
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
def test_emergency_alert(request):
    serializer = TestAlertSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create test alert
    alert = EmergencyAlert.objects.create(
        user=request.user,
        alert_type='test',
        message=serializer.validated_data['message']
    )

    # Here you would integrate with your notification service (Twilio, Firebase, etc.)
    # For now, we'll just return success
    print('alert success')

    return Response({
        'message': 'Test emergency alert sent successfully',
        'alert': EmergencyAlertSerializer(alert).data
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
        if not evidence.user_can_modify(request.user):
            return Response(
                {'error': 'You can only delete your own evidence'},
                status=status.HTTP_403_FORBIDDEN
            )
        
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