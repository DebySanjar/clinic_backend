"""
DentFlow — Survey Views
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .survey_models import Survey, Question, SurveyResponse, Answer
from .survey_serializers import (
    SurveyListSerializer, SurveyDetailSerializer, SurveyWriteSerializer,
    SurveyResponseSerializer, SurveyResponseWriteSerializer, QuestionSerializer,
)


# ─── Survey ViewSet ──────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(summary="So'rovnomalar ro'yxati", tags=['Surveys']),
    retrieve=extend_schema(summary="So'rovnoma tafsilotlari", tags=['Surveys']),
    create=extend_schema(summary="Yangi so'rovnoma yaratish", tags=['Surveys']),
    update=extend_schema(summary="So'rovnomani yangilash", tags=['Surveys']),
    partial_update=extend_schema(summary="So'rovnomani qisman yangilash", tags=['Surveys']),
    destroy=extend_schema(summary="So'rovnomani o'chirish", tags=['Surveys']),
)
class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SurveyWriteSerializer
        if self.action == 'retrieve':
            return SurveyDetailSerializer
        return SurveyListSerializer

    @extend_schema(summary="So'rovnomaga javoblar", tags=['Surveys'])
    @action(detail=True, methods=['get'], url_path='responses')
    def responses(self, request, pk=None):
        survey = self.get_object()
        qs = SurveyResponse.objects.filter(survey=survey).prefetch_related('answers__question')
        serializer = SurveyResponseSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(summary="So'rovnoma savollarini yangilash", tags=['Surveys'])
    @action(detail=True, methods=['put'], url_path='questions')
    def update_questions(self, request, pk=None):
        survey = self.get_object()
        survey.questions.all().delete()
        for i, q_data in enumerate(request.data):
            q_data['order'] = i
            s = QuestionSerializer(data=q_data)
            s.is_valid(raise_exception=True)
            Question.objects.create(survey=survey, **s.validated_data)
        return Response(SurveyDetailSerializer(survey).data)

    @extend_schema(summary="So'rovnoma statistikasi", tags=['Surveys'])
    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        survey = self.get_object()
        questions = survey.questions.all()
        result = []

        for q in questions:
            answers = Answer.objects.filter(question=q)
            entry = {
                'question_id':   q.id,
                'question_text': q.question_text,
                'question_type': q.question_type,
                'total_answers': answers.count(),
                'distribution':  {},
            }
            if q.question_type in ('radio', 'select', 'rating', 'scale'):
                from collections import Counter
                vals = answers.values_list('value', flat=True)
                entry['distribution'] = dict(Counter(vals))
            elif q.question_type == 'checkbox':
                import json
                from collections import Counter
                counter: Counter = Counter()
                for a in answers:
                    try:
                        items = json.loads(a.value)
                        if isinstance(items, list):
                            counter.update(items)
                    except Exception:
                        counter[a.value] += 1
                entry['distribution'] = dict(counter)
            result.append(entry)

        return Response({
            'survey_id':      survey.id,
            'title':          survey.title,
            'response_count': survey.response_count,
            'questions':      result,
        })


# ─── Public Survey Fill View ─────────────────────────────────────────────────

class PublicSurveyView(APIView):
    """Ommaviy — autentifikatsiyasiz"""
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Ommaviy so'rovnomani olish (slug bo'yicha)",
        tags=['Public Survey'],
    )
    def get(self, request, slug):
        try:
            survey = Survey.objects.prefetch_related('questions').get(slug=slug, status='active')
        except Survey.DoesNotExist:
            return Response({'error': "So'rovnoma topilmadi yoki faol emas"}, status=404)

        if survey.is_expired:
            return Response({'error': "So'rovnoma muddati tugagan"}, status=410)

        return Response(SurveyDetailSerializer(survey).data)

    @extend_schema(
        summary="So'rovnomani to'ldirish (javob yuborish)",
        request=SurveyResponseWriteSerializer,
        tags=['Public Survey'],
    )
    def post(self, request, slug):
        try:
            survey = Survey.objects.prefetch_related('questions').get(slug=slug, status='active')
        except Survey.DoesNotExist:
            return Response({'error': "So'rovnoma topilmadi"}, status=404)

        if survey.is_expired:
            return Response({'error': "So'rovnoma muddati tugagan"}, status=410)

        serializer = SurveyResponseWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validate required questions
        required_ids = set(
            survey.questions.filter(is_required=True).values_list('id', flat=True)
        )
        answered_ids = {a['question_id'] for a in data['answers']}
        missing = required_ids - answered_ids
        if missing:
            return Response(
                {'error': f"Majburiy savollar javobsiz qoldi: {list(missing)}"},
                status=400
            )

        # Get client IP
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')

        response_obj = SurveyResponse.objects.create(
            survey=survey,
            respondent_name=data.get('respondent_name', ''),
            respondent_phone=data.get('respondent_phone', ''),
            respondent_email=data.get('respondent_email', ''),
            ip_address=ip,
        )

        question_map = {q.id: q for q in survey.questions.all()}
        for ans in data['answers']:
            qid = ans['question_id']
            if qid in question_map:
                Answer.objects.create(
                    response=response_obj,
                    question=question_map[qid],
                    value=ans['value'],
                )

        return Response({'success': True, 'response_id': response_obj.id}, status=201)


# ─── Applicants View ─────────────────────────────────────────────────────────

class ApplicantsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Barcha arizachilar ro'yxati",
        parameters=[
            OpenApiParameter('survey_id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        ],
        tags=['Surveys'],
    )
    def get(self, request):
        qs = SurveyResponse.objects.select_related('survey').prefetch_related('answers__question')
        survey_id = request.query_params.get('survey_id')
        if survey_id:
            qs = qs.filter(survey_id=survey_id)
        serializer = SurveyResponseSerializer(qs, many=True)
        return Response(serializer.data)
