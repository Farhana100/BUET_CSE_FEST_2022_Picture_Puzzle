import math

from django.shortcuts import render
from user.models import *
from shomobay_shomiti_detector.models import *
from django.conf import settings


def HMModel(participant):
    print()
    print("in reweight------------------------------------------->>")

    # should contain 1 object for each adjacent participant
    subs = Submission.objects.filter(status=1, level=participant.curr_level - 1, participant__batch=participant.batch)

    print()
    print()
    update_list_weights = []
    update_list_max_weights = []
    for sub in subs:
        if sub.participant.user == participant.user:
            continue
        diff = (participant.last_successful_submission_time - sub.time).total_seconds()
        try:
            prev_weight1 = DetectorGraph.objects.get(participant1=participant, participant2=sub.participant)
            prev_weight2 = DetectorGraph.objects.get(participant1=sub.participant, participant2=participant)
        except DetectorGraph.DoesNotExist:
            # starting value of weight
            prev_weight1 = DetectorGraph.objects.create(participant1=participant, participant2=sub.participant,
                                                        weight=0)
            prev_weight2 = DetectorGraph.objects.create(participant1=sub.participant, participant2=participant,
                                                        weight=0)

        print("prev_weight ", prev_weight1.weight, prev_weight2.weight)

        # HMM
        new_weight = updateProbabilityForOneTimeStep(prev_weight1.weight)
        new_weight = reweighProbabilityBasedOnEvidence(new_weight, diff)

        prev_weight1.weight = new_weight
        prev_weight2.weight = new_weight
        # prev_weight1.save()
        # prev_weight2.save()
        update_list_weights.append(prev_weight1)
        update_list_weights.append(prev_weight2)

        # update max_weights
        if participant.max_weight <= new_weight:
            participant.max_weight = new_weight
            update_list_max_weights.append(participant)
        if sub.participant.max_weight <= new_weight:
            sub.participant.max_weight = new_weight
            update_list_max_weights.append(sub.participant)

        print(participant, sub.participant, diff, new_weight)

    DetectorGraph.objects.bulk_update(update_list_weights, ['weight'])
    Participant.objects.bulk_update(update_list_max_weights, ['max_weight'])
    print("out reweight------------------------------------------->>")
    print()


def EMMISSION1(time_diff):
    """
        time_diff in seconds
    """
    time_diff = time_diff / settings.SPREAD
    mean = settings.MEAN
    dev = settings.DEVIATION

    e_pow = -pow(math.log(time_diff, math.e) - mean, 2) / (2 * pow(dev, 2))
    p = pow(math.e, e_pow) / (pow(2 * math.pi, 0.5) * dev)

    return p


def EMMISSION0(time_diff):
    return settings.EMMISSION00 if EMMISSION1(time_diff) > 0.5 else settings.EMMISSION01


def updateProbabilityForOneTimeStep(B):
    """
    TRANSITION00 = 0.8     # -cheat(t+1)|-cheat(t)
    TRANSITION01 = 0.1     # -cheat(t+1)|+cheat(t)
    TRANSITION10 = 0.2     # +cheat(t+1)|-cheat(t)
    TRANSITION11 = 0.9     # +cheat(t+1)|+cheat(t)
    """
    return B * settings.TRANSITION11 + (1 - B) * settings.TRANSITION10


def reweighProbabilityBasedOnEvidence(B, evd):
    new_B = B * EMMISSION1(evd)
    new_B_ = (1 - B) * EMMISSION0(evd)

    return new_B / (new_B + new_B_)
