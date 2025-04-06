from django.contrib import admin, messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from django.contrib.auth.models import User
from .models import ChartOfAccounts, DisbursementVoucher, EmployeeAdvance
from persons.models import Employee # Keep this import
from decimal import Decimal

@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(ImportExportModelAdmin):
    list_display = ('account_number', 'name', 'account_type', 'account_subtype', 'parent_account', 'is_active', 'updated_at')
    list_filter = ('account_type', 'account_subtype', 'is_active', 'parent_account')
    search_fields = ('account_number', 'name', 'description', 'parent_account__name')
    list_editable = ('is_active',)
    autocomplete_fields = ('parent_account',)

@admin.register(DisbursementVoucher)
class DisbursementVoucherAdmin(ImportExportModelAdmin):
    list_display = (
        'dv_number', 'dv_date', 'payee_name', 'amount', 'status', 'project',
        'get_initiator_full_name', # Use full name display method
        'get_approved_by_1_full_name',
        'get_approved_by_final_full_name'
    )
    list_filter = ('status', 'dv_date', 'payment_method', 'bank_account', 'project')
    search_fields = ('dv_number', 'payee_name', 'notes', 'check_number', 'bank_account__name', 'project__name', 'initiator__username', 'initiator__first_name', 'initiator__last_name') # Search initiator name parts
    # Include base audit fields + new approver fields + display methods
    readonly_fields = (
        'created_at', 'updated_at', 'initiator', 'created_by', 'updated_by',
        'approved_by_1', 'approved_by_final',
        'get_initiator_full_name', 'get_created_by_full_name', 'get_updated_by_full_name',
        'get_approved_by_1_full_name', 'get_approved_by_final_full_name'
    )
    date_hierarchy = 'dv_date'
    # Include project in autocomplete
    autocomplete_fields = ('bank_account', 'project',)

    actions = ['submit_for_approval', 'approve_selected_items', 'reject_selected_items']

    # Fieldsets use full name display methods
    fieldsets = (
         (None, {'fields': ('dv_number', 'dv_date', 'project', 'payee_name', 'amount', 'status')}),
         ('Payment Details', {'fields': ('payment_method', 'check_number', 'bank_account')}),
         ('Auditing, Approval & Notes', {'fields': ('notes', 'initiator', 'get_created_by_full_name', 'get_updated_by_full_name', 'get_approved_by_1_full_name', 'get_approved_by_final_full_name', 'created_at', 'updated_at')}),
    )

    # --- Custom display methods for full names ---
    @admin.display(description='Initiator')
    def get_initiator_full_name(self, obj): return obj.initiator.get_full_name() if obj.initiator else None
    @admin.display(description='Created By')
    def get_created_by_full_name(self, obj): return obj.created_by.get_full_name() if obj.created_by else None
    @admin.display(description='Updated By')
    def get_updated_by_full_name(self, obj): return obj.updated_by.get_full_name() if obj.updated_by else None
    @admin.display(description='Approver 1')
    def get_approved_by_1_full_name(self, obj): return obj.approved_by_1.get_full_name() if obj.approved_by_1 else None
    @admin.display(description='Final Approver')
    def get_approved_by_final_full_name(self, obj): return obj.approved_by_final.get_full_name() if obj.approved_by_final else None
    # --- End custom display methods ---

    def save_model(self, request, obj, form, change):
        is_new = not change
        if is_new: obj.initiator = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        if is_new:
            obj.created_by = request.user
            update_list = ['created_by', 'initiator'] # Save both on create
            obj.save(update_fields=update_list)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser: return qs
        employee = getattr(request.user, 'employee_profile', None)
        if employee:
             # Show items initiated by user OR pending approval (any level)
             # Logic inside actions will determine if user can ACT on pending items
             pending_statuses = [self.model.DVStatus.PENDING_APPROVAL, self.model.DVStatus.PENDING_APPROVAL_2]
             return qs.filter(Q(initiator=request.user) | Q(status__in=pending_statuses))
        else: return qs.filter(initiator=request.user)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if 'status' not in readonly: readonly.append('status') # Status change via actions
        if obj:
            if obj.status != self.model.DVStatus.DRAFT or (request.user != obj.initiator and not request.user.is_superuser):
                all_field_names = [f.name for f in obj._meta.fields] + [f.name for f in obj._meta.many_to_many]
                always_editable_after_draft = ['notes'] # Allow notes editing?
                fields_to_make_readonly = [
                    f for f in all_field_names if f not in readonly and f not in always_editable_after_draft and f != 'id'
                ]
                readonly.extend(fields_to_make_readonly)
        return readonly

    # --- Admin Actions (Updated for new Status) ---
    @admin.action(description='Submit Selected %(verbose_name_plural)s for Approval')
    def submit_for_approval(self, request, queryset):
        updated_count = 0
        for item in queryset:
            if item.status == self.model.DVStatus.DRAFT and item.initiator == request.user:
                employee = getattr(item.initiator, 'employee_profile', None)
                manager = employee.manager if employee else None
                if manager and manager.user:
                    item.status = self.model.DVStatus.PENDING_APPROVAL # Start at L1 pending
                    item.approved_by_1 = None
                    item.approved_by_final = None
                    item.save(update_fields=['status', 'approved_by_1', 'approved_by_final', 'updated_by', 'updated_at'])
                    updated_count += 1
                else: self.message_user(request, f"Cannot submit {item}: Initiator has no manager assigned.", messages.ERROR)
            else: self.message_user(request, f"Cannot submit {item}: Invalid status ({item.status}) or not initiator.", messages.WARNING)
        if updated_count > 0: self.message_user(request, f"{updated_count} item(s) submitted.", messages.SUCCESS)

    @admin.action(description='Approve Selected %(verbose_name_plural)s')
    def approve_selected_items(self, request, queryset):
        approved_count, error_count, pending_l2_count = 0, 0, 0
        approver_user = request.user
        approver_employee = getattr(approver_user, 'employee_profile', None)
        if not approver_employee: self.message_user(request, "Approval Error: Your user is not linked to an Employee profile.", messages.ERROR); return

        for item in queryset:
            current_status = item.status
            initiator = item.initiator
            initiator_employee = getattr(initiator, 'employee_profile', None) if initiator else None

            if current_status not in [self.model.DVStatus.PENDING_APPROVAL, self.model.DVStatus.PENDING_APPROVAL_2]:
                 self.message_user(request, f"{item} is not pending approval.", messages.WARNING); continue
            if not initiator_employee:
                 self.message_user(request, f"Cannot process {item}: Initiator profile missing.", messages.ERROR); error_count += 1; continue

            manager_l1 = initiator_employee.manager
            manager_l1_user = manager_l1.user if manager_l1 else None
            manager_l2 = manager_l1.manager if manager_l1 else None
            manager_l2_user = manager_l2.user if manager_l2 else None

            required_approver_user = None
            is_l1_approval = False
            is_l2_approval = False

            if current_status == self.model.DVStatus.PENDING_APPROVAL and manager_l1_user:
                required_approver_user = manager_l1_user; is_l1_approval = True
            elif current_status == self.model.DVStatus.PENDING_APPROVAL_2 and manager_l2_user:
                required_approver_user = manager_l2_user; is_l2_approval = True

            if approver_user != required_approver_user:
                 req_app_name = required_approver_user.username if required_approver_user else 'N/A'
                 self.message_user(request, f"You ({approver_user}) are not required approver ({req_app_name}) for {item}.", messages.ERROR); error_count += 1; continue

            approver_limit = approver_employee.approval_limit or Decimal('0.00')
            can_ultimately_approve = approver_employee.can_ultimately_approve
            item_amount = item.amount or Decimal('0.00')

            try:
                if is_l1_approval:
                    needs_l2 = item_amount > approver_limit and not can_ultimately_approve
                    item.approved_by_1 = approver_user
                    item.updated_by = request.user # Record who updated
                    if not needs_l2:
                        item.approved_by_final = approver_user
                        item.status = self.model.DVStatus.APPROVED
                        item.save(update_fields=['status', 'approved_by_1', 'approved_by_final', 'updated_by', 'updated_at'])
                        approved_count += 1
                    else:
                        if not manager_l2_user:
                            self.message_user(request, f"Cannot approve {item}: Needs L2 approval, but L2 manager not found for {manager_l1}.", messages.ERROR); error_count += 1
                            item.approved_by_1 = None # Optional: revert L1 approval if L2 missing?
                            item.save(update_fields=['approved_by_1', 'updated_by', 'updated_at'])
                        else:
                            item.status = self.model.DVStatus.PENDING_APPROVAL_2 # Move to L2 pending
                            item.save(update_fields=['status', 'approved_by_1', 'updated_by', 'updated_at'])
                            pending_l2_count += 1
                elif is_l2_approval:
                    if item_amount <= approver_limit or can_ultimately_approve:
                        item.approved_by_final = approver_user
                        item.status = self.model.DVStatus.APPROVED
                        item.updated_by = request.user
                        item.save(update_fields=['status', 'approved_by_final', 'updated_by', 'updated_at'])
                        approved_count += 1
                    else:
                        self.message_user(request, f"Cannot approve {item}: Amount exceeds your final approval limit.", messages.ERROR); error_count += 1
            except Exception as e:
                 self.message_user(request, f"Error processing {item}: {e}", messages.ERROR); error_count += 1


        if approved_count > 0: self.message_user(request, f"{approved_count} item(s) approved.", messages.SUCCESS)
        if pending_l2_count > 0: self.message_user(request, f"{pending_l2_count} item(s) approved by L1, status set to Pending Approval (L2).", messages.INFO)

    @admin.action(description='Reject Selected %(verbose_name_plural)s')
    def reject_selected_items(self, request, queryset):
        rejected_count = 0
        approver_user = request.user
        for item in queryset:
             current_status = item.status
             if current_status not in [self.model.DVStatus.PENDING_APPROVAL, self.model.DVStatus.PENDING_APPROVAL_2]:
                  self.message_user(request, f"Cannot reject {item}: Not pending approval.", messages.WARNING); continue

             # Simple check: if pending, current user must be related as L1 or L2 manager
             initiator = item.initiator
             initiator_employee = getattr(initiator, 'employee_profile', None) if initiator else None
             manager_l1 = initiator_employee.manager if initiator_employee else None
             manager_l1_user = manager_l1.user if manager_l1 else None
             manager_l2 = manager_l1.manager if manager_l1 else None
             manager_l2_user = manager_l2.user if manager_l2 else None

             can_reject = False
             if current_status == self.model.DVStatus.PENDING_APPROVAL and approver_user == manager_l1_user:
                 can_reject = True
             elif current_status == self.model.DVStatus.PENDING_APPROVAL_2 and approver_user == manager_l2_user:
                 can_reject = True
             # Allow L1 to reject even if L2 is pending? Maybe not, let L2 reject. For now, only current required approver can reject.

             if can_reject:
                  item.status = self.model.DVStatus.REJECTED
                  # Clear only final approver? Keep L1 for history? Let's clear both for simplicity.
                  item.approved_by_1 = None
                  item.approved_by_final = None
                  item.updated_by = request.user
                  item.save(update_fields=['status', 'approved_by_1', 'approved_by_final', 'updated_by', 'updated_at'])
                  rejected_count += 1
             else:
                  req_app_name = 'N/A'
                  if current_status == self.model.DVStatus.PENDING_APPROVAL: req_app_name = manager_l1_user.username if manager_l1_user else 'L1 Manager'
                  elif current_status == self.model.DVStatus.PENDING_APPROVAL_2: req_app_name = manager_l2_user.username if manager_l2_user else 'L2 Manager'
                  self.message_user(request, f"Cannot reject {item}: You ({approver_user}) are not the required approver ({req_app_name}).", messages.ERROR)

        if rejected_count > 0: self.message_user(request, f"{rejected_count} item(s) rejected.", messages.SUCCESS)


@admin.register(EmployeeAdvance)
class EmployeeAdvanceAdmin(ImportExportModelAdmin):
    list_display = ('advance_number', 'employee', 'date_issued', 'amount_issued', 'project', 'status', 'date_due', 'get_is_overdue_display', 'balance_remaining', 'get_created_by_full_name')
    list_filter = ('status', 'employee', 'project', 'date_issued', 'date_due')
    search_fields = ('advance_number', 'employee__first_name', 'employee__last_name', 'purpose', 'project__name', 'asset_account__name')
    list_display_links = ('advance_number', 'employee')
    readonly_fields = ('balance_remaining', 'created_at', 'updated_at', 'created_by', 'updated_by', 'get_created_by_full_name', 'get_updated_by_full_name')
    date_hierarchy = 'date_issued'
    autocomplete_fields = ('employee', 'project', 'asset_account',)

    def get_fieldsets(self, request, obj=None):
        base_fieldsets = [
            (None, {'fields': ('advance_number', 'employee', 'asset_account', 'date_issued', 'amount_issued', 'purpose', 'project', 'date_due', 'status')}),
            ('Liquidation/Repayment', {'fields': ('amount_liquidated', 'amount_repaid', 'balance_remaining')}),
        ]
        audit_fields = ['created_at', 'get_created_by_full_name', 'updated_at', 'get_updated_by_full_name']
        # Hide audit section for non-superusers? Or just show limited info? Let's show.
        base_fieldsets.append(('Auditing', {'fields': audit_fields}))
        return base_fieldsets

    @admin.display(description='Overdue?', boolean=True)
    def get_is_overdue_display(self, obj): return obj.is_overdue
    @admin.display(description='Created By')
    def get_created_by_full_name(self, obj): return obj.created_by.get_full_name() if obj.created_by else None
    @admin.display(description='Updated By')
    def get_updated_by_full_name(self, obj): return obj.updated_by.get_full_name() if obj.updated_by else None

    def save_model(self, request, obj, form, change):
        is_new = not change
        # if is_new: obj.initiator = request.user # Add if Advance needs initiator tracking
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        if is_new:
            obj.created_by = request.user
            update_list = ['created_by']
            # if 'initiator' in [f.name for f in obj._meta.fields]: update_list.append('initiator')
            obj.save(update_fields=update_list)