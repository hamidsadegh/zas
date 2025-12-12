from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


from dcim.constants import RACK_U_HEIGHT_DEFAULT, RACK_U_HEIGHT_MAX, RACK_STARTING_UNIT_DEFAULT
from dcim.choices import (
    RackWidthChoices,
    RackStatusChoices,
    RackAirflowChoices,
    DeviceFaceChoices,
    RackDimensionUnitChoices,
    RackWeightUnitChoices,
    RackFormFactorChoices,
)
from dcim.models import Area


    
#
# Rack Types
#

class RackBase(models.Model):
    """
    Base class for RackType & Rack. Holds
    """
    width = models.PositiveSmallIntegerField(
        choices=RackWidthChoices,
        default=RackWidthChoices.WIDTH_19IN,
        verbose_name=_('width'),
        help_text=_('Rail-to-rail width')
    )

    # Numbering
    u_height = models.PositiveSmallIntegerField(
        default=RACK_U_HEIGHT_DEFAULT,
        verbose_name=_('height (U)'),
        validators=[MinValueValidator(1), MaxValueValidator(RACK_U_HEIGHT_MAX)],
        help_text=_('Height in rack units')
    )
    starting_unit = models.PositiveSmallIntegerField(
        default=RACK_STARTING_UNIT_DEFAULT,
        verbose_name=_('starting unit'),
        validators=[MinValueValidator(1)],
        help_text=_('Starting unit for rack')
    )
    desc_units = models.BooleanField(
        default=False,
        verbose_name=_('descending units'),
        help_text=_('Units are numbered top-to-bottom')
    )

    # Dimensions
    outer_width = models.PositiveSmallIntegerField(
        verbose_name=_('outer width'),
        blank=True,
        null=True,
        help_text=_('Outer dimension of rack (width)')
    )
    outer_height = models.PositiveSmallIntegerField(
        verbose_name=_('outer height'),
        blank=True,
        null=True,
        help_text=_('Outer dimension of rack (height)')
    )
    outer_depth = models.PositiveSmallIntegerField(
        verbose_name=_('outer depth'),
        blank=True,
        null=True,
        help_text=_('Outer dimension of rack (depth)')
    )
    outer_unit = models.CharField(
        verbose_name=_('outer unit'),
        max_length=50,
        choices=RackDimensionUnitChoices,
        blank=True,
        null=True
    )
    mounting_depth = models.PositiveSmallIntegerField(
        verbose_name=_('mounting depth'),
        blank=True,
        null=True,
        help_text=(_(
            'Maximum depth of a mounted device, in millimeters. For four-post racks, this is the distance between the '
            'front and rear rails.'
        ))
    )

    # Weight
    # WeightMixin provides weight, weight_unit, and _abs_weight
    max_weight = models.PositiveIntegerField(
        verbose_name=_('max weight'),
        blank=True,
        null=True,
        help_text=_('Maximum load capacity for the rack')
    )
    weight_unit = models.CharField(
        verbose_name=_('weight unit'),
        max_length=50,
        choices=RackWeightUnitChoices,
        blank=True,
        null=True
    )
    # Stores the normalized max weight (in grams) for database ordering
    _abs_max_weight = models.PositiveBigIntegerField(
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


class RackType(RackBase):
    """
    Devices are housed within Racks. Each rack has a defined height measured in rack units, and a front and rear face.
    Each Rack is assigned to a Area and (optionally) a Site.
    """
    form_factor = models.CharField(
        choices=RackFormFactorChoices,
        max_length=50,
        verbose_name=_('form factor')
    )
    vendor = models.ForeignKey(
        to='dcim.Vendor',
        on_delete=models.PROTECT,
        related_name='rack_types'
    )
    model = models.CharField(
        verbose_name=_('model'),
        max_length=100
    )

    clone_fields = (
        'vendor', 'form_factor', 'width', 'u_height', 'desc_units', 'outer_width', 'outer_height', 'outer_depth',
        'outer_unit', 'mounting_depth', 'weight', 'max_weight', 'weight_unit',
    )
    prerequisite_models = (
        'dcim.Vendor',
    )

    class Meta:
        ordering = ('vendor', 'model')
        constraints = (
            models.UniqueConstraint(
                fields=('vendor', 'model'),
                name='%(app_label)s_%(class)s_unique_vendor_model'
            ),
        )
        verbose_name = _('rack type')
        verbose_name_plural = _('rack types')

    def __str__(self):
        return self.model

    @property
    def full_name(self):
        return f"{self.vendor} {self.model}"
    

class Rack(RackBase):
    """
    Devices are housed within Racks. Each rack has a defined height measured in rack units, and a front and rear face.
    Each Rack is assigned to a Area and (optionally) a Site.
    """
    # Fields which cannot be set locally if a RackType is assigned
    RACKTYPE_FIELDS = (
        'form_factor', 'width', 'u_height', 'starting_unit', 'desc_units', 'outer_width', 'outer_height',
        'outer_depth', 'outer_unit', 'mounting_depth', 'weight', 'weight_unit', 'max_weight',
    )
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
        )
    name = models.CharField(
        verbose_name=_('name'),
        max_length=100,
        )
    description = models.TextField(
        verbose_name=_('description'),
        blank=True, 
        null=True
        )
    form_factor = models.CharField(
        choices=RackFormFactorChoices,
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('form factor')
    )
    rack_type = models.ForeignKey(
        to='dcim.RackType',
        on_delete=models.PROTECT,
        related_name='racks',
        blank=True,
        null=True,
    )
    facility_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('facility ID'),
        help_text=_("Locally-assigned identifier")
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name='racks',
    )
    status = models.CharField(
        verbose_name=_('status'),
        max_length=50,
        choices=RackStatusChoices,
        default=RackStatusChoices.STATUS_ACTIVE
    )
    serial = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('serial number')
    )
    airflow = models.CharField(
        verbose_name=_('airflow'),
        max_length=50,
        choices=RackAirflowChoices,
        blank=True,
        null=True
    )

    clone_fields = (
        'area', 'status', 'role', 'form_factor', 'width', 'airflow', 'u_height', 'desc_units',
        'outer_width', 'outer_height', 'outer_depth', 'outer_unit', 'mounting_depth', 'weight', 'max_weight',
        'weight_unit',
    )
    prerequisite_models = (
        'dcim.Area',
    )

    class Meta:
        unique_together = ("name", "area")
        verbose_name = "Rack"
        verbose_name_plural = "Racks"

    def __str__(self):
        return f"{self.area} / {self.name}"

    @property
    def site(self):
        """
        Convenience accessor to the rack's site, derived from its area.
        """
        return self.area.site if self.area else None
   



  

# class Rack(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=100)
#     area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="racks")
#     height = models.PositiveIntegerField(default=42, help_text="Rack height in U units")
#     description = models.TextField(blank=True, null=True)

#     class Meta:
#         unique_together = ("name", "area")
#         verbose_name = "Rack"
#         verbose_name_plural = "Racks"

#     def __str__(self):
#         return f"{self.area} / {self.name}"
   
