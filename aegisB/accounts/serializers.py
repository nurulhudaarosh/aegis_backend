from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser
from datetime import date

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = CustomUser
        fields = ('id', 'name', 'email', 'password', 'user_type', 'agent_id', 
                  'gender', 'phone', 'id_type', 'id_number', 'dob','blood_group','address','emergency_medical_note')
    
    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_dob(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value
    
    def validate(self, data):
        # Validate agent_id based on user_type
        user_type = data.get('user_type', 'user')
        agent_id = data.get('agent_id')
        
        if user_type == 'agent' and not agent_id:
            raise serializers.ValidationError({"agent_id": "Agent ID is required for agent users."})
        
        if user_type == 'user' and agent_id:
            raise serializers.ValidationError({"agent_id": "Agent ID should not be provided for regular users."})
        
        return data
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    agent_id = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        agent_id = data.get('agent_id')
        
        if not email or not password:
            raise serializers.ValidationError("Must provide both email and password.")
        
        user = authenticate(username=email, password=password)
        
        if not user:
            raise serializers.ValidationError("Unable to log in with provided credentials.")
        
        # Agent-specific checks
        if user.user_type == 'agent':
            if not agent_id:
                raise serializers.ValidationError("Agent ID is required for agent login.")
            if user.agent_id != agent_id:
                raise serializers.ValidationError("Invalid agent ID.")
        
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        
        data['user'] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'name', 'email', 'user_type', 'agent_id', 
                  'gender', 'phone', 'id_type', 'id_number', 'dob', 'blood_group',
                  'address', 'emergency_medical_note', 'profile_picture')
        read_only_fields = ('email', 'user_type', 'agent_id')


class ProfilePictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('profile_picture',)