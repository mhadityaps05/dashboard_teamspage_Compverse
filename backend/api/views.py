from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from .models import Competition, UserProfile, Registration, Team
from .serializers import (
    CompetitionSerializer, UserProfileSerializer, RegistrationSerializer, 
    TeamSerializer, UserSerializer, JoinTeamSerializer, ParticipantSerializer, 
    EmailTokenObtainPairSerializer
)
from .permissions import IsAdminOrReadOnly
from rest_framework.permissions import BasePermission, SAFE_METHODS

from supabase import create_client, Client
import os, uuid
from django.contrib.auth import get_user_model
from api.models import Competition
from django.db.models.functions import TruncDate
from django.db.models import Count
from datetime import timedelta, date


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User registered successfully!", "user_id": user.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompetitionViewSet(viewsets.ModelViewSet):
    queryset = Competition.objects.all()
    serializer_class = CompetitionSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['end_date', 'start_date']


    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        comp_type = self.request.query_params.get('type')
        if comp_type:
            queryset = queryset.filter(type=comp_type)
        return queryset

    @action(detail=True, methods=['get'], url_path='participants')
    def competition_participants(self, request, pk=None):
        competition = get_object_or_404(Competition, id=pk)
        participants = User.objects.filter(registration__competition=competition)
        serializer = ParticipantSerializer(participants, many=True)
        return Response({
            "competition_id": competition.id,
            "competition_title": competition.title,
            "participants": serializer.data
        })

    @action(detail=True, methods=['get'])
    def teams(self, request, pk=None):
        competition = get_object_or_404(Competition, id=pk)
        teams = Team.objects.filter(competition=competition)
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)

supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)


class UploadCompetitionPosterView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [AllowAny]

    def post(self, request, competition_id):
        competition = get_object_or_404(Competition, id=competition_id)
        if 'poster' not in request.FILES:
            return Response({"error": "No poster file provided"}, status=status.HTTP_400_BAD_REQUEST)

        poster_file = request.FILES['poster']
        ext = os.path.splitext(poster_file.name)[1]
        filename = f"competition_{competition_id}_{uuid.uuid4()}{ext}"

        try:
            supabase.storage.from_("competition-posters").upload(
                file=poster_file,
                path=filename,
                file_options={"content-type": poster_file.content_type}
            )
            url = supabase.storage.from_("competition-posters").get_public_url(filename)
            competition.poster_competition = url
            competition.save()
            return Response({"message": "Poster uploaded successfully", "poster_url": url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RegistrationViewSet(viewsets.ModelViewSet):
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['competition', 'user']
    ordering_fields = ['registered_at']

    def create(self, request, *args, **kwargs):
        user = request.user
        competition_id = request.data.get("competition")

        if Registration.objects.filter(user=user, competition_id=competition_id).exists():
            return Response({"error": "You are already registered for this competition!"}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [AllowAny]
    permission_classes = [permissions.IsAuthenticated] 
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['competition']
    search_fields = ['name']
    ordering_fields = ['created_at']

    @action(detail=True, methods=['post'], url_path='join')
    def join_team(self, request, pk=None):
        team = self.get_object()
        user = request.user

        if team.members.filter(id=user.id).exists():
            return Response({'detail': 'Anda sudah tergabung dalam tim ini.'}, status=status.HTTP_400_BAD_REQUEST)

        if team.members.count() >= team.competition.max_participants:
            return Response({"error": "Tim sudah mencapai batas maksimal anggota!"}, status=status.HTTP_400_BAD_REQUEST)

        team.members.add(user)
        return Response({'detail': 'Berhasil bergabung ke tim!'}, status=status.HTTP_200_OK)


class CreateTeamView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user
        team_name = request.data.get("team_name")
        competition_id = request.data.get("competition_id")

        if Team.objects.filter(name=team_name).exists():
            return Response({"error": "Team name already exists."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            competition = Competition.objects.get(id=competition_id)
        except Competition.DoesNotExist:
            return Response({"error": "Competition not found."}, status=status.HTTP_404_NOT_FOUND)

        team = Team.objects.create(name=team_name, leader=user, competition=competition)
        team.members.add(user)
        return Response({"message": "Team created successfully.", "team_id": team.id}, status=status.HTTP_201_CREATED)


class JoinTeamView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user
        team_id = request.data.get("team_id")

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response({"error": "Tim tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        if Team.objects.filter(members=user, competition=team.competition).exists():
            return Response({"error": "Anda sudah tergabung dalam tim lain dalam kompetisi ini."}, status=status.HTTP_400_BAD_REQUEST)

        team.members.add(user)
        return Response({"message": "Berhasil bergabung ke tim."}, status=status.HTTP_200_OK)


class RegisterCompetitionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user
        competition_id = request.data.get("competition_id")
        team_id = request.data.get("team_id")

        try:
            competition = Competition.objects.get(id=competition_id)
        except Competition.DoesNotExist:
            return Response({"error": "Competition not found"}, status=status.HTTP_404_NOT_FOUND)

        if Registration.objects.filter(user=user, competition=competition).exists():
            return Response({"error": "You are already registered for this competition."}, status=status.HTTP_400_BAD_REQUEST)

        if competition.type == "individual":
            Registration.objects.create(user=user, competition=competition)
            return Response({"message": "Successfully registered for the competition."}, status=status.HTTP_201_CREATED)

        if competition.type == "group":
            if not team_id:
                return Response({"error": "Team ID is required for group competitions."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return Response({"error": "Team not found"}, status=status.HTTP_404_NOT_FOUND)

            if team.members.filter(id=user.id).exists():
                Registration.objects.create(user=user, competition=competition, team=team)
                return Response({"message": "Successfully registered with the team."}, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": "You are not a member of this team."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()

class AnalyticsView(APIView):
    def get(self, request):
        # Rentang tanggal 30 hari terakhir
        today = date.today()
        start_date = today - timedelta(days=30)

        # Hitung user per tanggal
        user_counts = (
            User.objects.filter(date_joined__date__gte=start_date)
            .annotate(date=TruncDate('date_joined'))
            .values('date')
            .annotate(user=Count('id'))
        )

        # Hitung post lomba (Competition) per tanggal
        post_counts = (
            Competition.objects.filter(created_at__date__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(post=Count('id'))
        )

        # Gabung hasilnya jadi satu dict per tanggal
        combined = {}
        for u in user_counts:
            combined[u['date']] = {'date': u['date'], 'user': u['user'], 'post': 0}
        for p in post_counts:
            if p['date'] in combined:
                combined[p['date']]['post'] = p['post']
            else:
                combined[p['date']] = {'date': p['date'], 'user': 0, 'post': p['post']}

        # Ubah ke list dan sort by tanggal
        result = sorted(combined.values(), key=lambda x: x['date'])

        # Format tanggal jadi string
        for r in result:
            r['date'] = r['date'].isoformat()

        return Response(result)

class MyCompetitionsView(APIView):
    permission_classes =[IsAuthenticated]

    def get(self, request):
        registrations = Registration.objects.filter(user=request.user)
        competitions = [r.competition for r in registrations]
        serializer = CompetitionSerializer(competitions, many=True)
        return Response(serializer.data)
    
class MyTeamsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        led_teams = Team.objects.filter(leader=user)
        joined_teams = Team.objects.filter(members=user).exclude(leader=user)

        all_teams = led_teams.union(joined_teams)

        serializer = TeamSerializer(all_teams, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_dashboard(request):
    data = {
        "total_competitions": Competition.objects.count(),
        "total_users": User.objects.count(),
        "total_teams": Team.objects.count(),
        "total_registrations": Registration.objects.count(),
    }
    return Response(data)
