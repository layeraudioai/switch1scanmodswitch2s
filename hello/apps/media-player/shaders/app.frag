#version 450
#extension GL_GOOGLE_include_directive : require
layout(location=0) out vec4 outColor;
#define STATE_ACCESS readonly
#include "abi.glsl"
#include "draw.glsl"
void main(){
    vec2 p = gl_FragCoord.xy;
    vec3 color = mix(vec3(.04, .07, .14), vec3(.02, .15, .25), p.y / 1080.0);
    
    float panel = fill(box(p, vec2(960, 540), vec2(800, 520), 28));
    color = mix(color, vec3(.07, .13, .22), panel);

    float header = fill(box(p, vec2(960, 140), vec2(760, 70), 16));
    color = mix(color, vec3(.10, .22, .36), header);

    int selected = int(c.library.x);
    for (int i = 0; i < 6; i++) {
        float yPos = 230.0 + float(i * 75);
        float itemBox = fill(box(p, vec2(960, yPos + 30), vec2(760, 60), 12));
        vec3 itemColor = (i == selected) ? vec3(.18, .40, .60) : vec3(.09, .18, .28);
        color = mix(color, itemColor, itemBox);
        
        if (i == selected) {
            float badge = fill(box(p, vec2(230, yPos + 30), vec2(20, 40), 6));
            color = mix(color, vec3(.20, .85, .95), badge);
        }
    }

    float ctrlPanel = fill(box(p, vec2(960, 700), vec2(760, 70), 14));
    color = mix(color, vec3(.06, .12, .20), ctrlPanel);

    outColor = vec4(color * (1.0 - c.transition.x), 1);
}
