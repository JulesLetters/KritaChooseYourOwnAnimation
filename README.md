A tool to help make animations by allowing you to choose the next frame from a subset of specifically-named layers.

# Installation:
Follow the instructions under "manually" in https://docs.krita.org/en/user_manual/python_scripting/install_custom_python_plugin.html

That is, roughly, take the files from this repository, and place them in wherever Krita takes when you go to Settings > Manage Resources... > Open Resources.
Then restart Krita so it detects the plugin.

After the plugin is detected, we need to enable it:
1. Go to Settings > Configure Krita... and scroll down on the left to get to the Python Plugin Manager. 
2. Click to enable "Choose Your Own Animation", then click OK.
3. Restart Krita again.


Finally, select Settings > Dockers > Choose Your Own Animation.


# Operation:
Roughly, you will want to:
1. Import all frames you want to use into a Group Layer named "Frames".
2. Rename the frames to a pattern like this: `Long_Name (Aliases) - PossibleFutures`

   Example: `Bouncing002 (B2) - B3 C3`
3. Click 'Initialize / Reload'
4. Double-click displayed frames to start creating a sequence.
5. Rename the "Animation" layer, then use Layer > Convert > Convert group to animated layer


# Longer explanation:
This documentation will differentiate between a 'node', which will be the entire name of a layer in Krita, and a 'frame', which is named by the leftmost part of the node name (before the first space).

The plugin expects to find a top-level Group Layer named 'Frames'. This should contain Layers that will become the nodes you want to use and reuse in your animation. To populate Group Layer with other Layers, you'll likely decompose a GIF or other animation into frame files, then import those files into Krita using File > Import Animation Frames. Decomposition can be performed with ffmpeg, a tool which you will eventually need, though decomposition is a topic that will not be covered here.

The node names should be in the following format: `LongNodeName (Aliases) - PossibleFutures`

- The long name on the left must be unique in a given project, and will also be used as a file name.
- Aliases are simply alternate names for a frame, for convenience. If more than one node has the same alias, any node with that alias as a possible future node will list all nodes with that alias. 
- You can put text inside square brackets anywhere to make a comment that won't affect the program.
- Because of filename restrictions, nodes can't be named with any of: `/ \ : * ? " < > |`
- Examples:
```
   Bouncing_001 (B1) [Starting Frame] - B2 C1
   Bouncing_002 (B2) [Middle height] - B3 B1
   Bouncing_003 (B3) [Bottom height] - B2
   Bouncing_012 (C1) [Falls left] - C2
   Bouncing_013 (C2) - C3
   Bouncing_014 (C3) [Hits wall] - C2
   Bouncing_100 (D1 C1) [Curves right] - D2
   Bouncing_101 (D2) [Curves into other bounces] - D1 C2 B2
```

When you click "Initialize", a layer named Animation will be created, and possible future frames will load into the right window. With the "Current frame" textbox empty, all frames will be displayed. To limit the frames, type the frame name into the "Current frame" textbox.

When you double-click a frame, a number of matching frames provided by "Frames to add" are added to the Animation layer, and the current frame is changed to the clicked frame, and possible future frames are updated accordingly.

When you're done creating your animation, rename this layer (so that the plugin can regenerate another layer named "Animation" if needed), then use Layer > Convert > Convert group to animated layer. This will give you a finished animation that you can export from Krita.

To export animations You'll need to download ffmpeg.
Check out https://www.ffmpeg.org or https://docs.krita.org/en/reference_manual/render_animation.html#setting-up-krita-for-exporting-animations

From Krita, use File > Render Animation, switch to 'Video', and set the options as you need.


# Additional Details:
A folder named "cyoa_frames" will be created. While working, the frames will be exported to this directory, so they can be used to create the animation. While project descriptors are unique, this folder is not unique, which allows the frames to be reused between projects. However, because the plugin will clobber this folder, it is advisable to keep projects that do not share frames in different folders.

A file with the name of your krita file prefixed with "_cyoa_descriptor.json" will be created, which is modified whenever a frame is appended. This file contains the information that is needed to recreate the animation when "Reload" is clicked, and references the files in the "cyoa_frames" directory. It is possible to regenerate the animation from this file and the layers in the "Frames" Group Layer. To do this, delete the "cyoa_frames" folder, "Animation" layer, "Animation_Performance" layer, and click "Reload" in Krita. Note that if a frame name is changed after work has begun, it will need to be manually changed in this file.

A file named "frame_full_names.json" will be placed in "cyoa_frames". It describes how the file names link to the node names in Krita. It doesn't need to be changed, though is not used in the current plugin version.

You can nest folders in the "Frames" group, and treat them as folders. All leaf-level nodes will be treated as frames.

A layer named "Animation_Performance" will be created. It is used to speed up the process of appending new frames in Krita. It should not be touched and can remain collapsed.
