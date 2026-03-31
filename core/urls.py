from django.urls import path
from .views import (
    CreateNewsletterSlotView, NewsletterSlotDetailView, GenreSubgenreMappingView, 
    AddBookView, BookDetailView, ProfileDetailView, PublicProfileDetailView, BookManagementStatsView, 
    NewsletterStatsView, NotificationListView, TestWebSocketNotificationView, 
    NewsletterSlotExportView, SwapPartnerDiscoveryView, SwapRequestListView, SwapRequestDetailView,
    MyPotentialBooksView, SwapPartnerDetailView, RecentSwapHistoryView, NotificationUnreadCountView,
    SwapManagementListView, AcceptSwapView, RejectSwapView, RestoreSwapView,
    SwapHistoryDetailView, TrackMySwapView, CancelSwapView, AuthorReputationView,
    SubscriberVerificationView, ConnectMailerLiteView, SubscriberAnalyticsView, CampaignDatesView,
    CampaignAnalyticCreateView,
    RequestSwapPlacementView, AuthorDashboardView, AudienceSizeView,
    AllSwapRequestsView,
    EmailListView, ComposeEmailView, EmailDetailView, EmailActionView,
    ChatAuthorListView, ConversationListView, ChatHistoryView, SendMessageView,
    MySwapPartnersView, ComposePartnerListView, ChatMessageDetailView,
    CreateStripeCheckoutSessionView, CreateSwapCheckoutSessionView, SyncSwapPaymentView, ConfirmSwapPaymentView, StripeWebhookView, ChangePlanView,
    SetupIntentView, SavedPaymentMethodsView, DeletePaymentMethodView, SetDefaultPaymentMethodView,
    PreviewPlanChangeView, SyncSubscriptionView, UpgradeSubscriptionView,
    WalletView, WalletTransactionHistoryView, WithdrawFundsView, DirectPaymentView, AddFundsView, ConfirmAddFundsView,
    PaySwapWithWalletView,
)
from .calendar_views import (
    GoogleCalendarExportView, OutlookCalendarExportView, ICSExportView, CalendarExportOptionsView
)
from .ui_views import SlotExploreView, SlotDetailsView, SwapArrangementView, SharedSlotView




urlpatterns = [
    path('newsletter-slot/', CreateNewsletterSlotView.as_view(), name='create-newsletter-slot'),
    path('newsletter-slot/<int:pk>/', NewsletterSlotDetailView.as_view(), name='newsletter-slot-detail'),
    path('genre-mapping/', GenreSubgenreMappingView.as_view(), name='genre-subgenre-mapping'),
    path('add-book/', AddBookView.as_view(), name='add-book'),
    path('book/<int:pk>/', BookDetailView.as_view(), name='book-detail'),
    path('profile/', ProfileDetailView.as_view(), name='profile-detail'),
    path('profiles/<int:user_id>/', PublicProfileDetailView.as_view(), name='public-profile-detail'),
    path('book-management-stats/', BookManagementStatsView.as_view(), name='book-management-stats'),
    path('newsletter-dashboard/', NewsletterStatsView.as_view(), name='newsletter-dashboard'),
    path('newsletter-stats/', NewsletterStatsView.as_view(), name='newsletter-stats'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('test-notification/', TestWebSocketNotificationView.as_view(), name='test-notification'),
    path('newsletter-slot/<int:pk>/export/', NewsletterSlotExportView.as_view(), name='newsletter-slot-export'),
    path('swap-requests/', SwapRequestListView.as_view(), name='swap-request-list'),
    path('swap-requests/<int:pk>/', SwapRequestDetailView.as_view(), name='swap-request-detail'),
    path('my-books/', MyPotentialBooksView.as_view(), name='my-potential-books'),
    
    # --- Swap Management Page (Figma) ---
    path('swaps/', SwapManagementListView.as_view(), name='swap-management-list'),
    path('accept-swap/<int:pk>/', AcceptSwapView.as_view(), name='accept-swap'),
    path('reject-swap/<int:pk>/', RejectSwapView.as_view(), name='reject-swap'),
    path('restore-swap/<int:pk>/', RestoreSwapView.as_view(), name='restore-swap'),
    path('swap-history/<int:pk>/', SwapHistoryDetailView.as_view(), name='swap-history-detail'),
    path('track-swap/<int:pk>/', TrackMySwapView.as_view(), name='track-my-swap'),
    path('cancel-swap/<int:pk>/', CancelSwapView.as_view(), name='cancel-swap'),

    # --- Figma UI Specific APIs ---
    path('slots/explore/', SlotExploreView.as_view(), name='slots-explore'),
    path('slots/<int:pk>/details/', SlotDetailsView.as_view(), name='slots-details'),
    path('slots/<int:slot_id>/request/', SwapRequestListView.as_view(), name='slot-request-create'),
    path('slots/<int:slot_id>/request-placement/', RequestSwapPlacementView.as_view(), name='request-swap-placement'),
    path('swaps/<int:pk>/arrangement/', SwapArrangementView.as_view(), name='swaps-arrangement'),
    path('slots/shared/<uuid:token>/', SharedSlotView.as_view(), name='shared-slot'),
    
    # Reputation & Verification
    path('author-reputation/', AuthorReputationView.as_view(), name='author-reputation'),
    path('subscriber-verification/', SubscriberVerificationView.as_view(), name='subscriber-verification'),
    path('connect-mailerlite/', ConnectMailerLiteView.as_view(), name='connect-mailerlite'),
    path('subscriber-analytics/', SubscriberAnalyticsView.as_view(), name='subscriber-analytics'),
    path('campaign-dates/', CampaignDatesView.as_view(), name='campaign-dates'),
    path('campaign-analytics/create/', CampaignAnalyticCreateView.as_view(), name='campaign-analytics-create'),
    
    # Dashboard
    path('author-dashboard/', AuthorDashboardView.as_view(), name='author-dashboard'),
    path('audience-size/', AudienceSizeView.as_view(), name='audience-size'),
    path('all-swap-requests/', AllSwapRequestsView.as_view(), name='all-swap-requests'),

    # Email System
    path('emails/', EmailListView.as_view(), name='email-list'),
    path('emails/compose/', ComposeEmailView.as_view(), name='email-compose'),
    path('emails/<int:pk>/', EmailDetailView.as_view(), name='email-detail'),
    path('emails/<int:pk>/action/', EmailActionView.as_view(), name='email-action'),

    # Chat System
    path('chat/authors/', ChatAuthorListView.as_view(), name='chat-authors'),
    path('chat/conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('chat/history/<int:receiver_id>/', ChatHistoryView.as_view(), name='chat-history'),
    path('chat/compose/', ComposePartnerListView.as_view(), name='chat-compose'),
    path('chat/my-partners/', MySwapPartnersView.as_view(), name='my-partners'),
    path('chat/<int:user_id>/send/', SendMessageView.as_view(), name='send-message'),
    path('chat/message/<int:message_id>/', ChatMessageDetailView.as_view(), name='chat-message-detail'),

    # Stripe
    path('subscription/upgrade/', UpgradeSubscriptionView.as_view(), name='subscription-upgrade'),
    path('stripe/create-checkout-session/', CreateStripeCheckoutSessionView.as_view(), name='stripe-create-session'),
    path('stripe/create-swap-checkout-session/', CreateSwapCheckoutSessionView.as_view(), name='stripe-create-swap-session'),
    path('stripe/sync-swap-payment/', SyncSwapPaymentView.as_view(), name='stripe-sync-swap-payment'),
    path('stripe/confirm-swap-payment/<int:swap_request_id>/', ConfirmSwapPaymentView.as_view(), name='stripe-confirm-swap-payment'),
    path('payments/swap/wallet/', PaySwapWithWalletView.as_view(), name='pay-swap-wallet'),
    path('stripe/change-plan/', ChangePlanView.as_view(), name='stripe-change-plan'),
    path('stripe/change-plan/preview/', PreviewPlanChangeView.as_view(), name='stripe-change-plan-preview'),
    path('stripe/setup-intent/', SetupIntentView.as_view(), name='stripe-setup-intent'),
    path('stripe/sync-subscription/', SyncSubscriptionView.as_view(), name='stripe-sync-subscription'),
    path('stripe/payment-methods/', SavedPaymentMethodsView.as_view(), name='stripe-payment-methods'),
    path('stripe/payment-methods/<str:pm_id>/', DeletePaymentMethodView.as_view(), name='stripe-delete-payment-method'),
    path('stripe/payment-methods/<str:pm_id>/set-default/', SetDefaultPaymentMethodView.as_view(), name='stripe-set-default-pm'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),

    # Wallet & Payment System
    path('wallet/', WalletView.as_view(), name='wallet'),
    path('wallet/transactions/', WalletTransactionHistoryView.as_view(), name='wallet-transactions'),
    path('wallet/add-funds/', AddFundsView.as_view(), name='wallet-add-funds'),
    path('wallet/confirm-funds/', ConfirmAddFundsView.as_view(), name='wallet-confirm-funds'),
    path('wallet/withdraw/', WithdrawFundsView.as_view(), name='wallet-withdraw'),
    path('payments/direct/', DirectPaymentView.as_view(), name='direct-payment'),

    # Calendar Export
    path('calendar/google/', GoogleCalendarExportView.as_view(), name='calendar-google'),
    path('calendar/outlook/', OutlookCalendarExportView.as_view(), name='calendar-outlook'),
    path('calendar/ics/', ICSExportView.as_view(), name='calendar-ics'),
    path('calendar/options/', CalendarExportOptionsView.as_view(), name='calendar-options'),
]   