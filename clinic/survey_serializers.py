"""
DentFlow — Survey Serializers
"""
from rest_framework import serializers
from .survey_models import Survey, Question, SurveyResponse, Answer


# ─── Question ────────────────────────────────────────────────────────────────

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'question_type', 'options',
            'is_required', 'order', 'placeholder', 'help_text',
        ]


# ─── Survey ──────────────────────────────────────────────────────────────────

class SurveyListSerializer(serializers.ModelSerializer):
    response_count = serializers.IntegerField(read_only=True)
    question_count = serializers.SerializerMethodField()
    is_expired     = serializers.BooleanField(read_only=True)

    class Meta:
        model = Survey
        fields = [
            'id', 'title', 'description', 'status', 'slug',
            'is_anonymous', 'allow_multiple', 'expires_at',
            'response_count', 'question_count', 'is_expired',
            'created_at', 'updated_at',
        ]

    def get_question_count(self, obj) -> int:
        return obj.questions.count()


class SurveyDetailSerializer(serializers.ModelSerializer):
    questions      = QuestionSerializer(many=True, read_only=True)
    response_count = serializers.IntegerField(read_only=True)
    is_expired     = serializers.BooleanField(read_only=True)

    class Meta:
        model = Survey
        fields = [
            'id', 'title', 'description', 'status', 'slug',
            'is_anonymous', 'allow_multiple', 'expires_at',
            'questions', 'response_count', 'is_expired',
            'created_at', 'updated_at',
        ]


class SurveyWriteSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)

    class Meta:
        model = Survey
        fields = [
            'title', 'description', 'status',
            'is_anonymous', 'allow_multiple', 'expires_at', 'questions',
        ]

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        survey = Survey.objects.create(**validated_data)
        for i, q in enumerate(questions_data):
            q.setdefault('order', i)
            Question.objects.create(survey=survey, **q)
        return survey

    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if questions_data is not None:
            instance.questions.all().delete()
            for i, q in enumerate(questions_data):
                q.setdefault('order', i)
                Question.objects.create(survey=instance, **q)
        return instance


# ─── Answer & Response ───────────────────────────────────────────────────────

class AnswerWriteSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    value       = serializers.CharField(allow_blank=True)


class SurveyResponseWriteSerializer(serializers.Serializer):
    respondent_name  = serializers.CharField(required=False, allow_blank=True, default='')
    respondent_phone = serializers.CharField(required=False, allow_blank=True, default='')
    respondent_email = serializers.CharField(required=False, allow_blank=True, default='')
    answers          = AnswerWriteSerializer(many=True)

    def validate_answers(self, answers):
        return answers


class AnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)

    class Meta:
        model = Answer
        fields = ['id', 'question', 'question_text', 'question_type', 'value']


class SurveyResponseSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = SurveyResponse
        fields = [
            'id', 'survey', 'respondent_name', 'respondent_phone',
            'respondent_email', 'ip_address', 'submitted_at', 'answers',
        ]
