from django.contrib import admin, messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from django.contrib.auth.models import User
from .models import Bill, BillLine
from persons.models import Employee
from decimal import Decimal


class BillLineInline(admin.TabularInline):
    model = BillLine
    extra = 1
    fields = ('product', 'description', 'account', 'project', 'warehouse', 'quantity', 'unit_price', 'line_total', 'is_vatable', 'bir_classification')
    readonly_fields = ('line_total',)
    autocomplete_fields = ('product', 'account', 'project', 'warehouse')
    # TODO: Make inline readonly based on parent status

@admin.register(Bill)
class BillAdmin(ImportExportModelAdmin):
    list_display = (
        'bill_number', 'vendor', 'bill_date', 'total_amount', 'balance_due',
        'status', 'get_initiator_full_name', # Use full name display method
        'get_approved_by_1_full_name',
        'get_approved_by_final_full_name'
    )
    list_filter = ('status', 'vendor', 'bill_date', 'tags', 'disbursement_voucher')
    search_fields = ('bill_number', 'vendor__name', 'notes', 'disbursement_voucher__dv_number', 'initiator__username', 'initiator__first_name', 'initiator__last_name') # Search initiator name parts
    readonly_fields = (
        'subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due',
        'status', # Make status non-editable directly, use actions
        'created_at', 'updated_at', 'initiator', 'approved_by_1', 'approved_by_final',
        'get_initiator_full_name', 'get_created_by_full_name', 'get_updated_by_full_name',
        'get_approved_by_1_full_name', 'get_approved_by_final_full_name'
    )
    date_hierarchy = 'bill_date'
    filter_horizontal = ('tags',)
    inlines = [BillLineInline]
    autocomplete_fields = ('vendor', 'disbursement_voucher',)

    actions = ['submit_for_approval', 'approve_selected_items', 'reject_selected_items']

    # Fieldsets use full name display methods
    fieldsets = (
         (None, {'fields': ('vendor', 'bill_number', 'bill_date', 'due_date', 'status', 'disbursement_voucher')}),
         ('Amounts', {'fields': ('subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due')}),
         ('Categorization & Notes', {'fields': ('tags', 'notes')}),
         ('Auditing & Approval', {'fields': ('initiator', 'get_created_by_full_name', 'get_updated_by_full_name', 'get_approved_by_1_full_name', 'get_approved_by_final_full_name', 'created_at', 'updated_at')}),
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
            update_list = ['created_by', 'initiator']
            obj.save(update_fields=update_list)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser: return qs
        employee = getattr(request.user, 'employee_profile', None)
        if employee:
             # Show items initiated by user OR pending approval (any level)
             pending_statuses = [self.model.BillStatus.PENDING_APPROVAL, self.model.BillStatus.PENDING_APPROVAL_2]
             return qs.filter(Q(initiator=request.user) | Q(status__in=pending_statuses))
        else: return qs.filter(initiator=request.user)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        # Ensure status is always readonly in the form view
        if 'status' not in readonly: readonly.append('status')

        if obj:
            is_initiator = (request.user == obj.initiator)
            is_superuser = request.user.is_superuser

            # If not in DRAFT status and the user is not the initiator (unless superuser)
            if obj.status != self.model.BillStatus.DRAFT and not is_initiator and not is_superuser:
                # Make most fields read-only for non-initiators after submission
                all_field_names = [f.name for f in obj._meta.fields] + [f.name for f in obj._meta.many_to_many]
                always_editable = ['notes', 'tags', 'id'] # Example: Allow notes/tags editing?
                fields_to_make_readonly = [f for f in all_field_names if f not in readonly and f not in always_editable]
                readonly.extend(fields_to_make_readonly)
            elif obj.status != self.model.BillStatus.DRAFT and is_initiator and not is_superuser:
                 # If initiator tries to edit after submitting, make key fields readonly
                 key_fields = ['vendor', 'bill_number', 'bill_date', 'due_date', 'disbursement_voucher', 'amount_paid'] # etc.
                 readonly.extend([f for f in key_fields if f not in readonly])

        # Ensure inlines also become readonly after DRAFT? Requires customizing Inline's get_readonly_fields - more complex.

        return readonly

    # --- Admin Actions (Updated for PENDING_APPROVAL_2) ---
    @admin.action(description='Submit Selected %(verbose_name_plural)s for Approval')
    def submit_for_approval(self, request, queryset):
        updated_count = 0
        for item in queryset:
            if item.status == self.model.BillStatus.DRAFT and item.initiator == request.user:
                employee = getattr(item.initiator, 'employee_profile', None)
                manager = employee.manager if employee else None
                if manager and manager.user:
                    item.status = self.model.BillStatus.PENDING_APPROVAL # Start at L1 pending
                    item.approved_by_1 = None
                    item.approved_by_final = None
                    item.save(update_fields=['status', 'approved_by_1', 'approved_by_final', 'updated_by', 'updated_at'])
                    updated_count += 1
                else: self.message_user(request, f"Cannot submit Bill {item.bill_number}: Initiator has no manager assigned.", messages.ERROR)
            else: self.message_user(request, f"Cannot submit Bill {item.bill_number}: Invalid status ({item.status}) or not initiator.", messages.WARNING)
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

            if current_status not in [self.model.BillStatus.PENDING_APPROVAL, self.model.BillStatus.PENDING_APPROVAL_2]:
                 self.message_user(request, f"Bill {item.bill_number} is not pending approval.", messages.WARNING); continue
            if not initiator_employee:
                 self.message_user(request, f"Cannot process Bill {item.bill_number}: Initiator profile missing.", messages.ERROR); error_count += 1; continue

            manager_l1 = initiator_employee.manager
            manager_l1_user = manager_l1.user if manager_l1 else None
            manager_l2 = manager_l1.manager if manager_l1 else None
            manager_l2_user = manager_l2.user if manager_l2 else None

            required_approver_user = None
            is_l1_approval = False
            is_l2_approval = False

            if current_status == self.model.BillStatus.PENDING_APPROVAL and manager_l1_user:
                required_approver_user = manager_l1_user; is_l1_approval = True
            elif current_status == self.model.BillStatus.PENDING_APPROVAL_2 and manager_l2_user:
                required_approver_user = manager_l2_user; is_l2_approval = True

            if approver_user != required_approver_user:
                 req_app_name = required_approver_user.username if required_approver_user else 'N/A'
                 self.message_user(request, f"You ({approver_user}) are not required approver ({req_app_name}) for Bill {item.bill_number}.", messages.ERROR); error_count += 1; continue

            approver_limit = approver_employee.approval_limit or Decimal('0.00')
            can_ultimately_approve = approver_employee.can_ultimately_approve
            item_amount = item.total_amount or Decimal('0.00')

            try:
                if is_l1_approval:
                    needs_l2 = item_amount > approver_limit and not can_ultimately_approve
                    item.approved_by_1 = approver_user
                    item.updated_by = request.user
                    if not needs_l2: # Final approval by L1
                        item.approved_by_final = approver_user
                        item.status = self.model.BillStatus.APPROVED
                        item.save(update_fields=['status', 'approved_by_1', 'approved_by_final', 'updated_by', 'updated_at'])
                        approved_count += 1
                    else: # Needs L2
                        if not manager_l2_user:
                            self.message_user(request, f"Cannot approve Bill {item.bill_number}: Needs L2 approval, but L2 manager not found for {manager_l1}.", messages.ERROR); error_count += 1
                            item.approved_by_1 = None # Revert L1 approval maybe?
                            item.save(update_fields=['approved_by_1', 'updated_by', 'updated_at'])
                        else:
                            item.status = self.model.BillStatus.PENDING_APPROVAL_2 # Set L2 pending status
                            item.save(update_fields=['status', 'approved_by_1', 'updated_by', 'updated_at'])
                            pending_l2_count += 1
                elif is_l2_approval:
                    if item_amount <= approver_limit or can_ultimately_approve: # Final approval by L2
                        item.approved_by_final = approver_user
                        item.status = self.model.BillStatus.APPROVED
                        item.updated_by = request.user
                        item.save(update_fields=['status', 'approved_by_final', 'updated_by', 'updated_at'])
                        approved_count += 1
                    else: # Exceeds L2 limit
                        self.message_user(request, f"Cannot approve Bill {item.bill_number}: Amount exceeds your final approval limit.", messages.ERROR); error_count += 1
            except Exception as e:
                 self.message_user(request, f"Error processing Bill {item.bill_number}: {e}", messages.ERROR); error_count += 1

        if approved_count > 0: self.message_user(request, f"{approved_count} item(s) approved.", messages.SUCCESS)
        if pending_l2_count > 0: self.message_user(request, f"{pending_l2_count} item(s) approved by L1, status set to Pending Approval (L2).", messages.INFO)

    @admin.action(description='Reject Selected %(verbose_name_plural)s')
    def reject_selected_items(self, request, queryset):
        rejected_count = 0
        approver_user = request.user
        for item in queryset:
             current_status = item.status
             if current_status not in [self.model.BillStatus.PENDING_APPROVAL, self.model.BillStatus.PENDING_APPROVAL_2]:
                  self.message_user(request, f"Cannot reject Bill {item.bill_number}: Not pending approval.", messages.WARNING); continue

             initiator = item.initiator
             initiator_employee = getattr(initiator, 'employee_profile', None) if initiator else None
             manager_l1 = initiator_employee.manager if initiator_employee else None
             manager_l1_user = manager_l1.user if manager_l1 else None
             manager_l2 = manager_l1.manager if manager_l1 else None
             manager_l2_user = manager_l2.user if manager_l2 else None

             can_reject = False
             if current_status == self.model.BillStatus.PENDING_APPROVAL and approver_user == manager_l1_user:
                 can_reject = True
             elif current_status == self.model.BillStatus.PENDING_APPROVAL_2 and approver_user == manager_l2_user:
                 can_reject = True

             if can_reject:
                  item.status = self.model.BillStatus.REJECTED
                  item.approved_by_1 = None # Clear approval markers
                  item.approved_by_final = None
                  item.updated_by = request.user
                  item.save(update_fields=['status', 'approved_by_1', 'approved_by_final', 'updated_by', 'updated_at'])
                  rejected_count += 1
             else:
                  req_app_name = 'N/A'
                  if current_status == self.model.BillStatus.PENDING_APPROVAL: req_app_name = manager_l1_user.username if manager_l1_user else 'L1 Manager'
                  elif current_status == self.model.BillStatus.PENDING_APPROVAL_2: req_app_name = manager_l2_user.username if manager_l2_user else 'L2 Manager'
                  self.message_user(request, f"Cannot reject Bill {item.bill_number}: You ({approver_user}) are not the required approver ({req_app_name}).", messages.ERROR)

        if rejected_count > 0: self.message_user(request, f"{rejected_count} item(s) rejected.", messages.SUCCESS)


@admin.register(BillLine)
class BillLineAdmin(ImportExportModelAdmin):
    list_display = ('bill', 'account', 'project', 'warehouse', 'description', 'quantity', 'unit_price', 'line_total', 'is_vatable')
    list_filter = ('bill__vendor', 'account', 'project', 'warehouse', 'is_vatable')
    search_fields = ('description', 'bill__bill_number', 'product__name', 'account__name', 'project__name', 'warehouse__name')
    autocomplete_fields = ('bill', 'product', 'account', 'project', 'warehouse')
    readonly_fields = ('line_total',)