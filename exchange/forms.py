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
from dal import widgets as dalwidgets
from dal_select2 import widgets as ds2widgets
from django.utils.translation import ugettext as _
# Maybe we only want to autocomplete on Layers?
# from geonode.layers.models import Layer
from geonode.base.models import ResourceBase


class TextInputModelSelect2(dalwidgets.QuerySetSelectMixin,
                            ds2widgets.Select2WidgetMixin,
                            forms.TextInput):
    """Custom widget just to be a text I guess"""

class SearchForm(forms.Form):
    search_query = forms.ModelChoiceField(
        label=_("Content Search"),
        queryset=ResourceBase.objects.all(),
        #widget=forms.TextInput(),
        widget=TextInputModelSelect2(
            url='autocomplete_base',
            attrs={
                'data-placeholder': 'Search',
                'data-minimum-input-length': 3,
            })
    )
