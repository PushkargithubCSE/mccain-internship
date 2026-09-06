# Potato Box Damage Detection — Fine-Tuning Vision Foundation Models

## What this project does

This project teaches a computer to look at a photo of a potato shipping box (a cardboard carton) and figure out **whether it's damaged**, and **where** the damage is. This is the kind of check a factory quality-control line would want to automate — instead of a person inspecting every box by eye, a camera and a model do it.

Rather than building a model from scratch (which would need millions of images and huge amounts of compute), this project uses **fine-tuning**: starting from a large, already-trained "foundation model" — one that already understands general images very well — and teaching it the one new specific skill we need (spotting box damage) using a much smaller set of examples.

Two different models were fine-tuned and compared:

1. **RF-DETR** — draws a **box** around the damaged area ("damage is roughly here")
2. **SAM-3** — draws the **exact outline/shape** of the damaged area, pixel by pixel ("this precise shape is damage")

---

## Why fine-tuning, and what does that word actually mean?

A **foundation model** is a big neural network that has already been trained on a huge, general dataset (millions of everyday images) so it already understands shapes, textures, edges, and objects in general. It doesn't know anything specific about "cardboard box damage" yet — it just has strong general visual understanding.

**Fine-tuning** means taking that already-smart model and giving it a small, focused round of extra training on our specific problem (photos of boxes, labeled as damaged or not), so it adapts its existing knowledge to our task — without starting from zero.

This project deliberately did **not** just click a "train" button on a no-code platform. Every fine-tuning run was written and run manually, so the actual mechanics — what parts of the model get updated, what data goes in, what the loss numbers mean — are understood and explainable, not a black box.

---

## The general end-to-end pipeline (used for both models)

Regardless of which model was being fine-tuned, the overall process followed the same six stages:

### 1. Collect images
Since real photographs of damaged McCain shipping boxes weren't available, a small set of AI-generated photorealistic images of potato cartons (some damaged, some intact) was used instead. This is clearly documented as a limitation — in a real production setting, this step would use actual photos captured from the factory floor or conveyor line.

### 2. Annotate the images
Each image needs to be labeled so the model has something to learn from. This was done using **Roboflow**, a web tool for drawing labels on images.

- For the **box-detection** approach (RF-DETR): a rectangle ("bounding box") was drawn around each visible damage region.
- For the **segmentation** approach (SAM-3): a precise outline ("polygon") was traced around the exact edges of the damage.

The labeled dataset was then split into three groups:
- **Train** — images the model actually learns from
- **Validation (val)** — images used to check progress during training, without training on them
- **Test** — images kept completely hidden until the very end, used only to measure final real performance

### 3. Download and prepare the dataset
The annotated dataset was pulled from Roboflow into a cloud training environment (Google Colab, which provides free access to a GPU — a specialized chip that makes training neural networks much faster than a normal computer processor).

### 4. Load the foundation model and fine-tune it
The pretrained model (RF-DETR or SAM-3) was downloaded, and then trained further on the small annotated dataset. Both models used a strategy called **freezing**: most of the model's existing knowledge (its "encoder," the part that understands general images) was locked in place and not changed, while only a small, specific part of the model was actually updated during training. This is a common, efficient fine-tuning technique — it needs far less data and compute than retraining the whole model, and it avoids "forgetting" what the model already knows.

### 5. Evaluate on the test set
After training, the model was run on the held-out test images (ones it had never seen) to check whether it actually learned something useful, rather than just memorizing the training images.

### 6. Save and back up the trained model
Trained models were uploaded to **Hugging Face Hub**, a free cloud storage service specifically for AI models. This matters because the training environment (Colab) resets and deletes all files every time the session disconnects — so anything not saved elsewhere would be lost and need retraining from scratch.

---

## Approach 1: RF-DETR (box detection)

### What it outputs
A rectangle drawn around each detected damage region, with a confidence score (e.g., "87% sure this is damage").

### What RF-DETR actually is
RF-DETR is an object detection model built by Roboflow, based on an architecture family called **DETR** (short for "DEtection TRansformer"). Its image-understanding backbone is built on **DINOv2**, a well-known foundation model made by Meta AI — so even though the pivot moved away from a plain classification setup, the project is still genuinely "fine-tuning a vision foundation model" as originally intended.

### How it was fine-tuned
- The dataset was annotated with bounding boxes and exported in **COCO format** — a standard, widely-used file format for storing image annotations (named after the "Common Objects in Context" dataset it was originally built for).
- The model was fine-tuned using the `rfdetr` Python library, which handles most of the training loop internally — you configure things like how many training passes ("epochs") to run, batch size, and learning rate, and it manages the rest.
- **Early stopping** was used — the training automatically stops once the model stops improving on the validation set, instead of running a fixed number of epochs regardless of whether it's still learning. This avoids wasting time and avoids **overfitting** (a state where a model performs great on training data but poorly on new data, because it has essentially memorized the training examples instead of learning general patterns).

### Results
The best fine-tuning run reached a **mAP (mean Average Precision) of about 0.41–0.45** on the validation set. mAP is a standard object-detection scoring metric — roughly speaking, higher is better, and it measures how well the predicted boxes overlap with and correctly identify the real damage regions.

**Important honesty note:** the dataset used here was very small (around 10–15 images). This is nowhere near enough data to produce a trustworthy, production-grade accuracy number. What these results actually prove is that the **full pipeline works correctly end-to-end** — data loads, the model trains, checkpoints save, and predictions come out sensible on unseen images. A real deployment would need hundreds or thousands of labeled images per damage type to produce numbers you could actually trust.

### Extra: live training monitoring
**TensorBoard** (a standard tool for visualizing training progress — loss curves, accuracy over time, etc.) was connected to the training run, so progress could be watched live in a browser as training happened, rather than only reading text logs after the fact.

---

## Approach 2: SAM-3 (pixel-level segmentation)

### What it outputs
Instead of a rectangle, SAM-3 outputs a precise **mask** — a pixel-by-pixel outline of exactly where the damage is, following the real shape of the tear or hole rather than a rough box around it.

### What SAM-3 actually is
SAM-3 (Segment Anything Model 3) is Meta AI's newest foundation model for **segmentation** — the task of identifying the exact shape/outline of objects in an image, not just their rough location. Unlike a typical classifier which just says "yes/no," SAM-3 is a **promptable** model — you give it a text description (e.g., the word "damage") along with the image, and it tries to find and outline every matching region.

### An important engineering decision: SAM-3 vs SAM-2
SAM-3 was the original plan, but before committing to it, its actual hardware requirements were checked. SAM-3's official setup depends on a component (`flash-attn-3`) built for newer, more powerful GPUs than what's available on a typical laptop, and requesting access to its model weights required approval from Meta. Rather than assuming it would work and losing time to failed installs, this was tested deliberately (see Phase 0 environment check below) before writing any further code — a small but genuine example of validating assumptions before building on top of them, rather than discovering a hardware blocker halfway through a project.

Once GPU compatibility was confirmed (using a cloud GPU, since SAM-3 needs more graphics memory than a typical consumer laptop GPU provides) and checkpoint access was approved, the project proceeded with SAM-3 directly.

### How it was fine-tuned
- The dataset was re-annotated in Roboflow using **polygon** (outline-tracing) tools instead of boxes, and exported in a segmentation-specific COCO format.
- SAM-3 was loaded through Hugging Face's `transformers` library, which is a widely used Python library for working with pretrained AI models in a simple, consistent way.
- **Only the "mask decoder"** — the small part of the model responsible for producing the final outline shape — was fine-tuned. The much larger "vision encoder" (the part that understands general images, roughly 840 million of the model's parameters) was **frozen** and left untouched.
  - This meant only about **13.87 million parameters (1.65% of the whole model)** were actually being trained — a deliberate choice to fit within available GPU memory and to fine-tune efficiently with very little data, rather than risk destabilizing the model's already-strong general understanding.
- Training loss dropped steadily from its starting point down to roughly **0.007–0.01** across 20 training passes (epochs), and stayed stable rather than bouncing around — a good sign that the small decoder was learning consistently rather than randomly guessing.

### How it was evaluated
Since SAM-3 produces shapes (masks) rather than boxes, it needed different scoring metrics than RF-DETR:
- **IoU (Intersection over Union)** — how much the predicted shape overlaps with the real, correct shape. A perfect match scores 1.0; no overlap at all scores 0.
- **Dice score** — a closely related overlap metric, commonly used specifically for segmentation tasks, that's a bit more forgiving of small mismatches at the edges than IoU.

Both metrics were calculated on the 2 held-out test images, following the same "prove the pipeline works, don't over-trust the number" honesty applied to RF-DETR — 2 images is nowhere near enough to claim real-world reliability.

---

## Engineering lessons and honest limitations

A few things worth stating plainly, since they reflect real decisions made during the project rather than being hidden:

- **Tiny dataset.** All results here validate that the *fine-tuning pipeline* is built correctly — not that either model is production-ready. Real deployment needs a much larger, more varied labeled dataset (different lighting, box brands, camera angles, and damage types).
- **Cloud GPU, not local.** SAM-3's hardware requirements made local fine-tuning on a consumer laptop impractical, so training ran on Google Colab's free cloud GPU instead — a reasonable trade-off, and one that was tested and confirmed before committing time to it, rather than assumed.
- **Session persistence problems, solved.** Google Colab's free tier wipes all files whenever the session disconnects. This was solved by treating GitHub as the permanent home for code, and Hugging Face Hub as the permanent home for trained model weights — with checkpoints uploaded immediately after training finished, in the same step, to avoid losing completed work to a disconnect.
- **Simplified matching for SAM-3.** SAM-3 normally predicts 200 candidate shapes per image and is trained to match the single best one using a more complex matching algorithm. This project used a simplified version — just picking the single highest-confidence candidate — which is reasonable for a small dataset with one damage region per image, but is a simplification worth mentioning honestly rather than presenting as the "real" training method.

---

## Project structure

```
potato-finetuning/
├── data/                        # dataset splits, metadata
├── notebooks/                   # RF-DETR pipeline notebooks (phases 0–9)
├── src/                         # reusable Python code (dataset loaders, utils)
├── sam3/
│   ├── notebooks/                # SAM-3 pipeline notebooks (phases 0–4)
│   ├── checkpoints/               # local SAM-3 checkpoint output
│   └── src/
├── checkpoints/                 # local RF-DETR checkpoint output
├── report/                      # write-up and results summary
└── requirements.txt
```

Trained model weights for both approaches are hosted on Hugging Face Hub (not stored in this repository, due to file size):
- RF-DETR fine-tuned checkpoint: `PushkargithubCSE/rfdetr-potato-box-damage`
- SAM-3 fine-tuned checkpoint: `PushkargithubCSE/sam3-potato-box-damage`

---

## Summary

| | RF-DETR | SAM-3 |
|---|---|---|
| Output | Bounding box | Pixel-precise mask |
| Foundation model backbone | DINOv2 (via RF-DETR) | SAM-3's own vision encoder |
| What was fine-tuned | Full model (small dataset, early stopping) | Only the mask decoder (encoder frozen) |
| Trainable parameters | Full model | 13.87M / 840M (1.65%) |
| Annotation style | Bounding boxes | Polygons |
| Evaluation metric | mAP | IoU, Dice |
| Result | ~0.41–0.45 mAP | Loss converged to ~0.007–0.01 |
| Best fit for | "Is there damage, roughly where?" | "What is the exact shape of the damage?" |

Both approaches demonstrate the same core skill — taking a large pretrained vision model and adapting it to a new, specific task with limited data — using two different problem framings (detection vs. segmentation) and two different fine-tuning strategies (full fine-tune vs. frozen-encoder decoder-only fine-tune).