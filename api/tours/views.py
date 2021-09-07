from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from travelagency.models import Tour, TourImage
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from api.travelagencyAPI.serializers import TourSerializer, TourImageSerializer
import datetime
from django.db.models import Q
from django.contrib.sites.shortcuts import get_current_site
from touring.tests import OrderIdGenerator
from touring.models import Order, Payment,Failed_Order
from .serializers import OrderSerializer
from accounts.models import *
from rest_framework.authentication import TokenAuthentication, SessionAuthentication, BasicAuthentication
# Create your views here.

class TourAPIView(ListAPIView):
    queryset = Tour.objects.filter(publish_mode=True,last_booking_date__gte=str(datetime.date.today()),maximum_people__gte=1)
    serializer_class = TourSerializer
    pagination_class = PageNumberPagination


@api_view(['GET'])
def compareTourView(request):
    print("\nApi Entered\n")
    tour1 = request.GET.get('tour1')
    tour2 = request.GET.get('tour2')
    tourList=-1
    try:
        tour3 = request.GET.get('tour3')
        tourList=tourList+1
    except:
        print("Tour3 is not here... :|")
    try:
        tour4 = request.GET.get('tour4')
        tourList=tourList+1
    except:
        print("Tour4 is not here... :|")
    if tourList==-1 :
        tour_data = Tour.objects.filter(Q(tourId=tour1) | Q(tourId=tour2))
    elif tourList==0:
        tour_data = Tour.objects.filter(Q(tourId=tour1) | Q(tourId=tour2) | Q(tourId=tour3))
    elif tourList==1:
        tour_data = Tour.objects.filter(Q(tourId=tour1) | Q(tourId=tour2) | Q(tourId=tour3) | Q(tourId=tour4))

    print(tour_data)
    data = TourSerializer(tour_data, many=True)
    print("\n\n",data.data,"\n\n")
    return Response(
        {
            'status':200,
            'tour_data':data.data
        }
    )

class SearchTour(APIView):
    def get(self,request):
        try:
            sLocation = request.GET.get('sLocation')
            eLocation = request.GET.get('eLocation')
        except Exception as problem:
            return Response(
                {
                    'status':406,
                    'message':problem
                },
                status = status.HTTP_406_NOT_ACCEPTABLE
            )
        if sLocation != None and eLocation != None:
            tour1 = Tour.objects.filter(startingLocation__icontains=sLocation,endLocation__icontains=eLocation,publish_mode = True,
            last_booking_date__gte=str(datetime.date.today()),maximum_people__gte=1)
            tour2 = Tour.objects.filter(Q(tourHeading__icontains = sLocation) | Q(tourHeading__icontains = eLocation),publish_mode = True,
                last_booking_date__gte=str(datetime.date.today()),maximum_people__gte=1)
            tours = tour1.union(tour2)
            tour_data = TourSerializer(tours,many=True)
            return Response(
                {
                    'status':200,
                    'tours':tour_data.data
                },
                status = status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    'status':406,
                    'message':"sLocation and eLocation can not be NULL"
                },
                status = status.HTTP_406_NOT_ACCEPTABLE
            )

class AdvancedSearch(APIView):
     def get(self,request):
        try:
            startLocSearch = request.GET.get('startLocSearch')
            endLocSearch = request.GET.get('endLocSearch')
            startDateSearch = request.GET.get('startDateSearch')
            endDateSearch = request.GET.get('endDateSearch')
            startPrice= request.GET.get('startPrice')
            endPrice = request.GET.get('endPrice')
            minDuration=request.GET.get('minDuration')
            maxDuration = request.GET.get('maxDuration')
        except Exception as problem:
            return Response(
                {
                    'status':406,
                    'message':problem
                },
                status = status.HTTP_406_NOT_ACCEPTABLE
            )
        tour1 = Tour.objects.filter(startingLocation__icontains=startLocSearch,endLocation__icontains=endLocSearch,
        publish_mode = True,startDate__gte=startDateSearch,endDate__lte=endDateSearch,price__gte=startPrice,price__lte=endPrice,
        last_booking_date__gte=str(datetime.date.today()),maximum_people__gte=1)
        tours = []
        for i in tour1:
            day = i.startDate - i.endDate
            if day>=minDuration and day<=maxDuration:
                tours.append(i)
        tour_data = TourSerializer(tours,many=True)
        return Response(
            {
                'status':200,
                'tours':tour_data.data
            },
            status = status.HTTP_200_OK
        )


@api_view(['GET'])
def TourDetailsAPIView(request,slug):
    try:
        tour = Tour.objects.get(tourSlug=slug)
        tourimages =TourImage.objects.get(tour=tour)
    except Exception as e:
        print(e)
        exception = {
            'status':404,
            'message':'Does Not Exist'
        }
        return Response(data=exception,status = status.HTTP_404_NOT_FOUND)
    data1 = TourSerializer(tour)
    data2 = TourImageSerializer(tourimages)
    description_data = data1.data['description'].split('@@@@')
    description = []
    for i in description_data:
        lst = i.split('$$$$')
        description.append(lst)
    day_title = []
    day_description = []
    for i in description:
        day_title.append(i[0])
        day_description.append(i[1])
    data1 = dict(data1.data)
    data1['description']={
        'day_title':day_title,
        'day_description':day_description
    }
    data1['agentId']=tour.seller.userAccess.agentId
    link = 'http://'+ str(get_current_site(request).domain)
    images = list(dict(data2.data.items()).values())
    mimg = []
    for i in range(1,len(images)-1):
        if(images[i]!=None):
            images[i]=link+str(images[i])
            mimg.append(images[i])
    main_data = {
        'tourdata':data1,
        'tourimages':mimg,
        'weblink':link
    }
    return Response(data = main_data, status = status.HTTP_200_OK)
    
    

class BookTourAPI(APIView):
    authentication_classes = (TokenAuthentication,SessionAuthentication,BasicAuthentication)
    def post(self,request,tourId,agentId):
        if request.session.session_key:
            if request.session['access_type']=='traveller':
                user = request.user
                if Tour.objects.filter(tourId=tourId,maximum_people__gte=1).exists() and AccountType.objects.filter(agentId=agentId).exists():
                    seller_account = AccountType.objects.get(agentId=agentId)
                    if Tour.objects.filter(tourId=tourId,seller=seller_account.user).exists():
                        tour = Tour.objects.get(tourId=tourId,seller=seller_account.user)
                        ttl_people = int(request.data['total_people']) 
                        print(ttl_people)
                        if ttl_people>tour.maximum_people:
                            return Response(
                                data={
                                    'status':405,
                                    'message':"Don't even try!"

                                },
                                status = status.HTTP_405_METHOD_NOT_ALLOWED
                            )
                        elif(ttl_people<=0):
                            return Response(
                                data={
                                    'status':405,
                                    'message':"Don't even try!"

                                },
                                status = status.HTTP_405_METHOD_NOT_ALLOWED
                            )
                        else:
                            data = request.data
                            data['order_id']=OrderIdGenerator()
                            data['customer']=request.user.id
                            data['agent'] = tour.seller.id
                            data['agency'] = tour.seller.userAgency.id
                            total_payment = tour.price * int(data['total_people'])
                            data['total_price']=total_payment
                            data['paid_by_user']=round(total_payment*(10/100),2)
                            data['tour']=tour.id
                            orderSerializer = OrderSerializer(data=data)
                            if orderSerializer.is_valid():
                                order = orderSerializer.save()
                                return Response(
                                    data = {
                                        'status':200,
                                        'ORDER_ID':order.order_id,
                                        "CUST_ID" : order.customer.userAccess.userId,
                                        "MOBILE_NO" : order.customer_phone,
                                        "EMAIL" : order.customer_email,
                                        "TXN_AMOUNT" : str(order.paid_by_user),
                                    },
                                    status = status.HTTP_200_OK
                                )
                            else:
                                return Response(
                                    data={
                                        'status':500,
                                        'error':orderSerializer.errors
                                    },
                                    status = status.HTTP_500_INTERNAL_SERVER_ERROR
                                )
                    else:
                        return Response(
                            data = {
                                'status':400,
                                'error':'BAD REQUEST'
                            },
                            status = status.HTTP_400_BAD_REQUEST
                        )
                else:
                    return Response(
                            data = {
                                'status':403,
                                'error':'Not Allowed'
                            },
                            status = status.HTTP_403_FORBIDDEN
                        )
            else:
                return Response(
                    data ={
                    'status':401,
                    'error':"Unauthorized"
                    },
                    status=status.HTTP_401_UNAUTHORIZED

                )
        else:
            return Response(
                data = {
                    'status':403,
                    'error':"Unauthenticated"
                },
                status=status.HTTP_403_FORBIDDEN

            )
class AcceptPayment(APIView):    
    authentication_classes = (TokenAuthentication,SessionAuthentication,BasicAuthentication)
    def post(self,request):
        if request.session.session_key:
            if request.session['access_type']=='traveller':
                data = request.data
                order = Order.objects.get(order_id=data['ORDER_ID'])
                if order.paid_by_user == float(data['TXNAMOUNT']) and data['STATUS']==True:
                    confirm_order = Payment(
                        Order = order,
                        transaction_id=data['TXNID'],
                        banktransaction_id = data['BANKTXNID'],
                        txn_date = data['TXNDATE'],
                        gateway_name = data['GATEWAYNAME'],
                        bankname = data['BANKNAME'],
                        payment_mode = data['PAYMENTMODE'],
                    )
                    confirm_order.save()
                    order.status = True
                    order.save()
                    tour = order.tour
                    sit_left = tour.maximum_people - order.total_people
                    tour.maximum_people = sit_left if sit_left>0 else 0
                    tour.save()
                    return Response(
                        data={
                            'bill-context':{
                            "transactionId" : confirm_order.transaction_id,
                            "bankTransactionId" : confirm_order.banktransaction_id,
                            "orderId" : confirm_order.Order.order_id,
                            "date" : data['TXNDATE'] ,
                            "CMail" : confirm_order.Order.customer_email,
                            "CPhone" : confirm_order.Order.customer_phone,
                            "CName" : confirm_order.Order.customer_name,
                            "CAddress" : confirm_order.Order.customer_address,
                            "tourId" : confirm_order.Order.tour.tourId,
                            "startdate" : confirm_order.Order.tour.startDate,
                            "endDate" : confirm_order.Order.tour.endDate,
                            "startLocation" : confirm_order.Order.tour.startingLocation,
                            "endLoaction" : confirm_order.Order.tour.endLocation,
                            "placedBy" : confirm_order.Order.customer.userAccess.userId,
                            "Quentity" : confirm_order.Order.total_people,
                            "price":confirm_order.Order.paid_by_user,
                            "total_price":confirm_order.Order.total_price,
                            "To_be_paid":confirm_order.Order.total_price - confirm_order.Order.paid_by_user,
                            'orderDate':confirm_order.creation_date,
                            "agentId":confirm_order.Order.agent.userAccess.agentId,
                            "AgencyId":confirm_order.Order.agency.agency_Id,
                            'ppp':confirm_order.Order.tour.price,
                            'total_people':confirm_order.Order.total_people
                            }
                        },
                        status = status.HTTP_200_OK
                    )
                else:
                    failed_order = Failed_Order(
                    order_id=order.order_id,
                    customer = order.customer,
                    customer_email = order.customer_email,
                    customer_phone = order.customer_phone,
                    customer_name = order.customer_name,
                    customer_address = order.customer_address,
                    agent = order.agent,
                    agency=order.agency,
                    tour=order.tour,
                    creation_date = order.creation_date,
                    paid_by_user = order.paid_by_user,
                    total_price = order.total_price,
                    total_people=order.total_people
                    )
                    failed_order.save()
                    order.delete()
                    return Response(
                        data = {
                            'status':200,
                            'message':"Order Failed"
                        }
                    )
            else:
                return Response(
                    data = {
                        'status':401,
                        'error':"Unauthorized"
                    },
                    status = status.HTTP_401_UNAUTHORIZED
                )
        else:
            return Response(
                data = {
                    'status':403,
                    'error':"Forbidden"
                },
                status = status.HTTP_403_FORBIDDEN
            )
                    





            
