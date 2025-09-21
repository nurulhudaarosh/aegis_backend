from rest_framework import serializers
from .models import EmergencyContact
from django.contrib.auth import get_user_model

User = get_user_model()

class EmergencyContactSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    
    class Meta:
        model = EmergencyContact
        fields = ('id', 'name', 'phone', 'email', 'relationship', 'is_emergency_contact', 
                 'is_primary', 'photo', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_photo(self, obj):
        # Return emoji based on relationship
        relationship_emojis = {
            'family': '👨‍👩‍👧‍👦',
            'friend': '👥',
            'colleague': '💼',
            'neighbor': '🏠',
            'emergency_service': '🚨',
            'other': '👤'
        }
        return relationship_emojis.get(obj.relationship, '👤')
    
    def validate_phone(self, value):
        # Basic phone validation
        if not value.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            raise serializers.ValidationError("Phone number must contain only digits and valid symbols.")
        return value

class EmergencyContactCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ('name', 'phone', 'email', 'relationship', 'is_emergency_contact', 'is_primary')
    
    def validate_phone(self, value):
        if not value.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            raise serializers.ValidationError("Phone number must contain only digits and valid symbols.")
        return value

class UserWithContactsSerializer(serializers.ModelSerializer):
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    emergency_contacts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'emergency_contacts', 'emergency_contacts_count')
    
    def get_emergency_contacts_count(self, obj):
        return obj.emergency_contacts.count()

class PhoneLookupSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    
    def validate_phone(self, value):
        if not value.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            raise serializers.ValidationError("Invalid phone number format.")
        return value

class UserLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('name', 'email', 'phone')