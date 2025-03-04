from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
from .models import LeakAppMasterData, LeakAppResult, LeakAppShowReport, LeakAppTest

def get_highest_value_within_timer(part_number, timer):
    """Fetch the highest filter_values within the given timer for the part_number."""
    time_threshold = now() - timer
    highest_value = LeakAppResult.objects.filter(
        part_number=part_number, date__gte=time_threshold
    ).order_by('-filter_values').values_list('filter_values', flat=True).first()
    return highest_value if highest_value else 0

@receiver(post_save, sender=LeakAppResult)
def check_leak_status(sender, instance, **kwargs):
    """Signal to check leak status based on setpoint and timer values."""
    master_data = instance.part_number

    # Get highest value within timer1
    highest_value_timer1 = get_highest_value_within_timer(master_data, master_data.timer1)

    # Determine status based on setpoint1
    if highest_value_timer1 > master_data.setpoint1:
        status = "NOK"
    else:
        status = "OK"

    # Get highest value within timer2
    highest_value_timer2 = get_highest_value_within_timer(master_data, master_data.timer2)

    # Determine status based on setpoint2
    if highest_value_timer2 > master_data.setpoint2:
        status = "NOK"

    # Update the LeakAppResult status
    instance.status = status
    instance.save(update_fields=['status'])

    # Save results in LeakAppShowReport
    LeakAppShowReport.objects.create(
        batch_counter=instance.batch_counter,
        part_number=instance.part_number,
        filter_values=instance.filter_values,
        filter_no=instance.filter_no,
        status=status,
        shift=instance.shift,
        highest_value=max(highest_value_timer1, highest_value_timer2),
    )