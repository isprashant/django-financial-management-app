from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from wallets.models import WalletTransaction
from django.core.exceptions import ValidationError
from django.db.models import Q

User = settings.AUTH_USER_MODEL
# Create your models here.

class Movie(TimeStampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    release_year = models.PositiveIntegerField(null=True, blank=True)
    imdb_url = models.URLField(blank=True, null=True)
    poster_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title


class PropertyListing(TimeStampedModel):
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    area_sqft = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_inr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    property_type = models.CharField(max_length=100)  # land, flat, plot, etc.

    def __str__(self):
        return f"{self.title} ({self.location})"
    

class TaskType(TimeStampedModel):
    TYPE_CHOICES = [
        ("RATE_MOVIE", "rate_movie"),
        ("RATE_PROPERTY", "rate_property")
    ]
    code = models.CharField(max_length=50, choices=TYPE_CHOICES, default='RATE_MOVIE')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
    
class UserTask(TimeStampedModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("REJECTED", "Rejected"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
    task_type = models.ForeignKey(TaskType, on_delete=models.PROTECT)
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    # one of these will be filled based on task_type
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, null=True, blank=True, related_name="tasks"
    )
    property_listing = models.ForeignKey(
        PropertyListing, on_delete=models.CASCADE, null=True, blank=True, related_name="tasks"
    )

    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="User rating (1–5 stars).",
    )
    reward_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="INR/points actually credited for this task.",
    )
    wallet_txn = models.OneToOneField(
        WalletTransaction, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"]),
        ]

        # Prevent duplicate tasks for SAME target on SAME day
        constraints = [
            models.UniqueConstraint(
                fields=["user", "task_type", "date", "movie"],
                condition=Q(movie__isnull=False),
                name="unique_movie_task_per_day",
            ),
            models.UniqueConstraint(
                fields=["user", "task_type", "date", "property_listing"],
                condition=Q(property_listing__isnull=False),
                name="unique_property_task_per_day",
            ),
        ]
    
    def clean(self):
        """
        Enforce:
        - RATE_MOVIE -> movie must be set, property_listing must be None
        - RATE_PROPERTY -> property_listing must be set, movie must be None
        """
        if not self.task_type:
            return

        code = (self.task_type.code or "").upper()

        if code == "RATE_MOVIE":
            if not self.movie:
                raise ValidationError("RATE_MOVIE task must have a movie set.")
            if self.property_listing is not None:
                raise ValidationError(
                    "RATE_MOVIE task cannot have a property_listing set."
                )

        if code == "RATE_PROPERTY":
            if not self.property_listing:
                raise ValidationError("RATE_PROPERTY task must have a property set.")
            if self.movie is not None:
                raise ValidationError(
                    "RATE_PROPERTY task cannot have a movie set."
                )

    def __str__(self):
        return f"{self.user} - {self.task_type} - {self.date}"


class UserPointsSnapshot(TimeStampedModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="points_snapshot"
    )
    active_points = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
