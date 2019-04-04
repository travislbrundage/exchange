# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2019 Planet Federal
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

from django import forms
from dal import autocomplete
from django.utils.translation import ugettext as _
from geonode.layer.models import Layer
from geonode.base.models import ResourceBase


class SearchForm(forms.Form):
    text_query = forms.ModelChoiceField(
        label=_("Content Search"),
        max_length=100,
        queryset=ResourceBase.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='autocomplete-layer',
            attrs={
                'data-placeholder': 'Search',
                'data-minimum-input-length': 3,
            })
    )
