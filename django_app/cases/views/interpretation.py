from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_synergy.cases.models import Case
from django_synergy.cases.models.interpretation import InterpretationData
from django_synergy.cases.permissions import CanCreateInterpretation, CanEditInterpretation, \
    CanViewInterpretationList, CanViewInterpretationDetail
from django_synergy.cases.serializers.interpretation import InterpretationDataSerializer, \
    InterpretationDataWritableSerializer, InterpretationDataListSerializer, \
    InterpretationDataRetrieveSerializer, InterpretationDataDetailSerializer
from django_synergy.events.models import Event
from django_synergy.utils.views import BaseViewset

from datetime import datetime
from datetime import date
from collections import namedtuple

Range = namedtuple('Range', ['start', 'end'])


def YMD(date):
    dt = datetime.strptime(date, '%d-%m-%Y')
    return dt.year, dt.month, dt.day


class InterpretationDataViewSet(BaseViewset):
    queryset = InterpretationData.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': InterpretationDataSerializer,
        'create': InterpretationDataWritableSerializer,
        'list': InterpretationDataListSerializer,
        'retrieve': InterpretationDataRetrieveSerializer,
        'update': InterpretationDataWritableSerializer,
        'partial_update': InterpretationDataWritableSerializer,
    }

    def get_serializer_context(self):
        context = super(InterpretationDataViewSet, self).get_serializer_context()
        return context

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewInterpretationList]
        elif self.action == "create":
            self.permission_classes = [CanCreateInterpretation]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewInterpretationDetail]
        elif self.action == "update":
            self.permission_classes = [CanEditInterpretation]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditInterpretation]
        elif self.action == "destroy":
            self.permission_classes = [CanEditInterpretation]
        elif self.action == "details":
            self.permission_classes = [CanCreateInterpretation]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        data = request.data
        interpretations = InterpretationData.objects.filter(case__slug=data["case"])
        if interpretations.count() > 0:
            to_year1, to_month1, to_day1 = YMD(data["date_to"])
            from_year1, from_month1, from_day1 = YMD(data["date_from"])
            r1 = Range(start=datetime(from_year1, from_month1, from_day1), end=datetime(to_year1, to_month1, to_day1))
            for interpretation in interpretations:
                to_year2, to_month2, to_day2 = YMD(interpretation.date_to.strftime('%d-%m-%Y'))
                from_year2, from_month2, from_day2 = YMD(interpretation.date_from.strftime('%d-%m-%Y'))
                r2 = Range(start=datetime(from_year2, from_month2, from_day2),
                           end=datetime(to_year2, to_month2, to_day2))
                latest_start = max(r1.start, r2.start)
                earliest_end = min(r1.end, r2.end)
                delta = (earliest_end - latest_start).days + 1
                if delta > 0:
                    return Response(
                        {"status": "failed",
                         "message": "Can't create interpretation as dates are overlapping with other interpretation of this case"}
                        , status=status.HTTP_400_BAD_REQUEST)

        interpretation_serializer = InterpretationDataWritableSerializer(data=data,
                                                                         context=self.get_serializer_context())

        if interpretation_serializer.is_valid(raise_exception=True):
            interpretation_serializer_data = interpretation_serializer.validated_data
            interpretation_data = interpretation_serializer.save()

            events = Event.objects.filter(case__slug=data["case"])
            for event in events:
                to_year, to_month, to_day = YMD(data["date_to"])
                from_year, from_month, from_day = YMD(data["date_from"])
                between_year, between_month, between_day = YMD(event.event_date_time.strftime('%d-%m-%Y'))
                d2 = date(between_year, between_month, between_day)
                d1 = date(from_year, from_month, from_day)
                d3 = date(to_year, to_month, to_day)
                if d1 <= d2 <= d3:
                    event.is_interpreted = True
                    event.save()

            return Response(status=status.HTTP_200_OK,
                            data={"success": True,
                                  "data": InterpretationDataRetrieveSerializer(interpretation_data,
                                                                               many=False).data})

    def list(self, request, *args, **kwargs):
        case_slug = request.query_params.get('case', None)
        self.queryset = self.queryset.filter(case__slug=case_slug)
        return super().list(self, request, *args, **kwargs)

    @action(["get"], detail=False)
    def details(self, request, *args, **kwargs):
        case_slug = request.query_params.get('case', None)
        date_to = request.query_params.get('date_to', None)
        date_from = request.query_params.get('date_from', None)
        case = Case.objects.get(slug=case_slug)

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "data": InterpretationDataDetailSerializer(case, many=False, context={"date_to": date_to,
                                                                                                    "date_from": date_from}).data})
