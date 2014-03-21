from webapp2_extras.routes import RedirectRoute

from handlers.admin import AdminHandler
from handlers.contact import ContactHandler
from handlers.errors import Handle500
from handlers.funding_source import FundingSourceHandler
from handlers.home import HomeHandler
from handlers.login import LoginHandler
from handlers.organization import OrganizationHandler
from handlers.partner import PartnerHandler
from handlers.profile import ProfileHandler
from handlers.signup import SignupHandler
from handlers.staff import StaffHandler
from handlers.static import PublicStaticHandler
from handlers.transaction import TransactionHandler


__all__ = ['application_routes']

application_routes = []

_route_info = [
    # Public (static) handlers.
    ('about', 'GET', '/about',
        PublicStaticHandler('about.haml'), 'get'),
    ('copyright', 'GET', '/copyright',
        PublicStaticHandler('landing.haml'), 'get'),
    ('faq', 'GET', '/faq',
        PublicStaticHandler('landing.haml'), 'get'),
    ('features', 'GET', '/features',
        PublicStaticHandler('landing.haml'), 'get'),
    ('privacy', 'GET', '/privacy',
        PublicStaticHandler('landing.haml'), 'get'),
    ('terms', 'GET', '/terms',
        PublicStaticHandler('landing.haml'), 'get'),

    # Public handlers.
    ('contact', None, '/contact', ContactHandler, 'contact'),
    ('home', 'GET', '/', HomeHandler, 'home'),
    ('signup', None, '/signup', SignupHandler, 'signup'),
    ('partner', None, '/partner', PartnerHandler, 'send_partner_request'),
    ('profile.activate', 'GET', '/activate', SignupHandler, 'activate'),

    # Authentication-related handlers.
    ('login', None, '/login', LoginHandler, 'login'),
    ('logout', 'GET', '/logout', LoginHandler, 'logout'),
    ('forgot-password', None, '/forgot-password',
        LoginHandler, 'forgot_password'),

    # Invitation handlers.
    # ('invitation.send', 'POST', '/invitations/send',
    #     InvitationHandler, 'send'),
    # ('invitation.accept', None, '/invitations/accept',
    #     InvitationHandler, 'accept'),

    # Profile-related functionality.
    ('profile.view', 'GET', '/profile', ProfileHandler, 'view'),
    ('profile.update', None, '/profile/update', ProfileHandler, 'update'),

    # Funding source handlers.
    ('funding_source.create', 'POST', '/funding-source/create',
        FundingSourceHandler, 'create'),
    ('funding_source.create_stripe_customer', 'POST',
        '/funding-source/create-stripe-customer',
        FundingSourceHandler, 'create_stripe_customer'),
    ('funding_source.delete', 'POST', '/funding-source/delete',
        FundingSourceHandler, 'delete'),
    ('funding_source.delete_stripe_customer', 'POST',
        '/funding-source/delete-stripe-customer', FundingSourceHandler,
        'delete_stripe_customer'),

    # Transaction handlers.
    ('transaction.add_credit', None, '/transactions/add-credit',
        TransactionHandler, 'add_credit'),
    ('transaction.purchase', None, '/transactions/purchase/<id:\d+>',
        TransactionHandler, 'purchase'),
    ('transaction.purchase_list', 'GET', '/transactions/purchase',
        TransactionHandler, 'purchase_list'),
    ('transaction.process', 'POST', '/transactions/process',
        TransactionHandler, 'process'),
    ('transaction.refresh', 'GET', '/transactions/refresh',
        TransactionHandler, 'refresh'),
    ('transaction.transfer', None, '/transactions/transfer',
        TransactionHandler, 'transfer'),
    ('transaction.verify', 'GET', '/transactions/verify',
        TransactionHandler, 'verify'),
    ('transaction.view', 'GET', '/transactions/view/<id:\d+>',
        TransactionHandler, 'view'),

    # Organization handlers.
    ('organization.view', 'GET', '/organizations/<id:\d+>',
        OrganizationHandler, 'view'),
    ('organization.edit', None, '/organizations/<id:\d+>/edit',
        OrganizationHandler, 'edit'),
    ('organization.create_staff', 'POST',
        '/organizations/<id:\d+>/staff/create', OrganizationHandler,
        'create_staff'),
    ('organization.toggle_active', 'POST',
        '/organizations/staff/toggle-active', OrganizationHandler,
        'toggle_active'),

    # Admin handlers.
    ('admin.add_organization', None, '/admin/add-organization',
        AdminHandler, 'add_organization'),
    ('admin.deposit', None, '/admin/deposit', AdminHandler,
        'deposit'),
    ('admin.history', 'GET', '/admin/history', AdminHandler,
        'history'),

    # Error reporting handlers.
    ('error.report', 'POST', '/error/report', Handle500, 'get'),

    # Staff handlers.
    ('staff.deposit', None, '/staff/deposit', StaffHandler, 'deposit'),
    ('staff.home', 'GET', '/staff/home', StaffHandler, 'home'),
    ('staff.login', None, '/staff/login', StaffHandler, 'login'),
    ('staff.logout', 'GET', '/staff/logout', StaffHandler, 'logout'),
    ('staff.process_verify', 'POST', '/staff/process-verify', StaffHandler,
        'process_verify'),
    ('staff.refund', 'POST', '/staff/refund', StaffHandler, 'refund'),
    ('staff.update', None, '/staff/update', StaffHandler, 'update'),
    ('staff.verify', 'POST', '/staff/verify', StaffHandler, 'verify'),

]

for name, methods, pattern, handler_cls, handler_method in _route_info:
  # Allow a single string, but this has to be changed to a list.
  if isinstance(methods, basestring):
    methods = [methods]

  # Create the route.
  route = RedirectRoute(name=name, template=pattern, methods=methods,
                        handler=handler_cls, handler_method=handler_method,
                        strict_slash=True)

  # Add the route to the proper public list.
  application_routes.append(route)
