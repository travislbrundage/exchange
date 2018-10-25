# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo, (C) 2018 Boundless Spatial
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

from django.contrib.auth.decorators import login_required
from exchange.remoteservices.forms import ExchangeCreateServiceForm
from geonode.services.forms import ServiceForm
from geonode.services import enumerations
from geonode.services.models import Service, HarvestJob
from exchange.remoteservices import tasks
import logging
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render_to_response
from exchange.utils import get_bearer_token
from exchange.remoteservices.serviceprocessors.handler \
    import get_service_handler
from django.utils.translation import ugettext as _
from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from geonode.services.views import _gen_harvestable_ids
from django.template import RequestContext
from exchange.core.models import ExchangeProfile
from geonode.people.models import Profile

logger = logging.getLogger("geonode.core.layers.views")


@login_required
def services(request):
    """This view shows the list of all registered services"""
    profile = Profile.objects.get(username=request.user)
    try:
        profile = ExchangeProfile.objects.get(user=profile)
    except ExchangeProfile.DoesNotExist:
        pass
    return render(
        request,
        "services/service_list.html",
        {"services": Service.objects.all(),
         "profile": profile,}
    )


@login_required
def register_service(request):
    service_register_template = "services/service_register.html"
    profile = Profile.objects.get(username=request.user)
    try:
        profile = ExchangeProfile.objects.get(user=profile)
    except ExchangeProfile.DoesNotExist:
        pass
    if request.method == "POST" and \
            (profile.service_manager is True or
             profile.is_staff is True or profile.is_superuser is True):
        form = ExchangeCreateServiceForm(request.POST)
        if form.is_valid():
            service_handler = form.cleaned_data["service_handler"]
            service = service_handler.create_geonode_service(
                owner=request.user)
            service.full_clean()
            service.save()
            service.keywords.add(*service_handler.get_keywords())
            service.set_permissions({'users': {
                ''.join(request.user.username):
                    ['services.change_service', 'services.delete_service']
            }})
            if service_handler.indexing_method == enumerations.CASCADED:
                service_handler.create_cascaded_store()
            request.session[service_handler.url] = service_handler
            logger.debug("Added handler to the session")
            messages.add_message(
                request,
                messages.SUCCESS,
                _("Service registered successfully")
            )
            result = HttpResponseRedirect(
                reverse("edit_service",
                        kwargs={"service_id": service.id})
            )
        else:
            result = render(request, service_register_template, {"form": form,
                                                                 "profile": profile})
    else:
        form = ExchangeCreateServiceForm()
        result = render(
            request, service_register_template, {"form": form,
                                                 "profile": profile})
    return result


@login_required
def edit_service(request, service_id):
    """
    Edit an existing Service
    """
    service_obj = get_object_or_404(Service, pk=service_id)

    if request.method == "POST":
        service_form = ServiceForm(
            request.POST, instance=service_obj, prefix="service")
        if service_form.is_valid():
            service_obj = service_form.save(commit=False)
            service_obj.keywords.clear()
            service_obj.keywords.add(*service_form.cleaned_data['keywords'])
            service_obj.save()
            return HttpResponseRedirect(reverse(
                "harvest_resources", kwargs={"service_id": service_id}))
    else:
        service_form = ServiceForm(
            instance=service_obj, prefix="service")

    return render_to_response("services/service_edit.html",
                              RequestContext(request,
                                             {"service": service_obj,
                                              "service_form": service_form}))


def _get_service_handler(request, service):
    """Add the service handler to the HttpSession.

    We use the django session object to store the service handler's
    representation of the remote service between sequentially logic steps.
    This is done in order to improve user experience, as we avoid making
    multiple Capabilities requests (this is a time saver on servers that
    feature many layers.

    """

    headers = {'Authorization': "Bearer {}".format(
        get_bearer_token(valid_time=30, request=request))}

    service_handler = get_service_handler(
        service.base_url, service.type, headers=headers)
    request.session[service.base_url] = service_handler
    logger.debug("Added handler to the session")
    return service_handler


@login_required()
def harvest_resources(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    try:
        handler = request.session[service.base_url]
    except KeyError:  # handler is not saved on the session, recreate it
        return redirect(
            reverse("rescan_service", kwargs={"service_id": service.id})
        )
    available_resources = handler.get_resources()
    is_sync = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    if request.method == "GET":
        already_harvested = HarvestJob.objects.values_list(
            "resource_id", flat=True).filter(service=service)
        not_yet_harvested = [r for r in available_resources
                             if str(r.id) not in already_harvested]
        not_yet_harvested.sort(key=lambda resource: resource.id)
        paginator = Paginator(
            not_yet_harvested, getattr(settings, "CLIENT_RESULTS_LIMIT", 100))
        page = request.GET.get('page')
        try:
            harvestable_resources = paginator.page(page)
        except PageNotAnInteger:
            harvestable_resources = paginator.page(1)
        except EmptyPage:
            harvestable_resources = paginator.page(paginator.num_pages)
        result = render(
            request,
            "services/service_resources_harvest.html",
            {
                "service_handler": handler,
                "service": service,
                "importable": not_yet_harvested,
                "resources": harvestable_resources,
                "is_sync": is_sync,
            }
        )
    elif request.method == "POST":
        requested = request.POST.getlist("resource_list")
        resources_to_harvest = []
        for id in _gen_harvestable_ids(requested, available_resources):
            logger.debug("id: {}".format(id))
            harvest_job, created = HarvestJob.objects.get_or_create(
                service=service,
                resource_id=id,
            )
            if created:
                resources_to_harvest.append(id)
                tasks.harvest_resource.apply_async(
                    args=[harvest_job.id],
                    kwargs={'headers': {
                        'Authorization': "Bearer {0}".format(
                            get_bearer_token(valid_time=30,
                                             request=request))}},
                )
            else:
                logger.warning(
                    "resource {} already has a harvest job".format(id))
        msg_async = _("The selected resources are being imported")
        msg_sync = _("The selected resources have been imported")
        messages.add_message(
            request,
            messages.SUCCESS,
            msg_sync if is_sync else msg_async
        )
        go_to = (
            "harvest_resources" if handler.has_unharvested_resources(
                service) else "service_detail"
        )
        result = redirect(reverse(go_to, kwargs={"service_id": service.id}))
    else:
        result = None
    return result


@login_required()
def harvest_single_resource(request, service_id, resource_id):
    service = get_object_or_404(Service, pk=service_id)
    handler = _get_service_handler(request, service)
    try:  # check that resource_id is valid for this handler
        handler.get_resource(resource_id)
    except KeyError:
        raise Http404()
    harvest_job, created = HarvestJob.objects.get_or_create(
        service=service,
        resource_id=resource_id,
    )
    if not created and harvest_job.status == enumerations.IN_PROCESS:
        raise HttpResponse(
            _("Resource is already being processed"), status=409)
    else:
        tasks.harvest_resource.apply_async(
            args=[harvest_job.id],
            kwargs={'headers': {'Authorization': "Bearer {0}".format(
                get_bearer_token(valid_time=30, request=request))}},
        )
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Resource {} is being processed".format(resource_id))
    )
    return redirect(
        reverse("service_detail",
                kwargs={"service_id": service.id})
    )


@login_required
def rescan_service(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    try:
        _get_service_handler(request, service)
    except Exception:
        return render(
            request,
            "services/remote_service_unavailable.html",
            {"service": service}
        )
    print("Finished rescaning service. About to redirect back...")
    messages.add_message(
        request, messages.SUCCESS, _("Service rescanned successfully"))
    return redirect(
        reverse("harvest_resources", kwargs={"service_id": service_id}))
