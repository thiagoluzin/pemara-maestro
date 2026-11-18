"""Deterministic identity/style direction for the existing H3 photo route."""
from video_request import resolve_video_request


def photo_animation_direction(prompt: str, *, content_kind: str, camera_pose: str) -> str:
    # Already directed documents keep their exact dialogue and shot structure.
    if 'integrated_multimodal_description:' in prompt:
        return prompt
    plan = resolve_video_request(prompt, camera_pose=camera_pose)
    style = {
        'animation': 'The shot stays in the exact illustrated or animated visual style of the reference throughout; it never becomes live action.',
        'live_action': 'The photographic appearance of the original people and scene stays consistent throughout.',
        'mixed': 'Each photographed or illustrated element retains its own original visual treatment throughout.',
    }.get(content_kind, '')
    camera = {
        'Static': 'The camera and framing remain fixed.',
        'Follow Action': 'The camera smoothly tracks the requested action, keeping the original cast visible.',
        'Zoom Out': 'A slow small zoom out preserves the complete cast and scene.',
        'Zoom In': 'A slow small zoom in keeps the original cast visible.',
        'Pan Right': 'The camera pans gently right while preserving the original cast.',
        'Pan Left': 'The camera pans gently left while preserving the original cast.',
        'Pan Up': 'The camera tilts gently up.',
        'Pan Down': 'The camera tilts gently down.',
        'ClockWise (CW)': 'A small clockwise camera arc preserves the original cast.',
        'Anti Clockwise (ACW)': 'A small counterclockwise camera arc preserves the original cast.',
    }.get(plan['camera_pose'], 'The camera and framing remain fixed.')
    speech = plan['prompt']
    motion = {
        'run': 'Animate full running strides for each subject asked to run: alternating left and right foot push-offs and landings, lifted knees, opposite arm swings and visible body weight transfer. Keep running during dialogue. Preserve distinct stride phases for multiple runners. Pursuers follow behind when requested. The bodies articulate continuously; camera movement alone does not fulfill the action.',
        'walk': 'Animate a continuous walking cycle for each subject asked to walk: alternating planted feet, swing legs, opposite arms and visible weight transfer. Preserve the requested direction and each subject identity. Continue the walk during any dialogue.',
    }.get(plan['motion'], 'Carry out the requested action with visible changes in pose over time. If no specific action is given, animate the existing poses naturally without inventing a new activity. Camera movement alone does not animate the subjects.')
    sound = ('Only the explicitly supplied dialogue is spoken; scene directions are never narrated.'
        if '<d>' in speech else 'All subjects are silent. No dialogue, narration, singing or reading of the instructions.')
    return (f'Animate the existing complete image in one continuous shot. {style} '
        'Keep every original subject, recognizable facial identity, clothing, objects, lettering, '
        'colors and visual style throughout. Expressions, limb poses and positions change as required by the action. The image is the scene '
        'to animate, not an introduction to a different scene. Preserve the original cast '
        'and setting without substitutions or unrelated scene changes. '
        f'{camera} The owner requests: {speech} '
        f'{motion} Do not force a return to the opening pose unless a loop or final reference was explicitly supplied. {sound}')
