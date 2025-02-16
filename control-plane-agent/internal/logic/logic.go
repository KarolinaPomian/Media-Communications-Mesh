/*
 * SPDX-FileCopyrightText: Copyright (c) 2024 Intel Corporation
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

package logic

import (
	"context"
	"fmt"

	"github.com/sirupsen/logrus"

	"control-plane-agent/internal/event"
	"control-plane-agent/internal/logic/actions"
)

type logicController struct {
	manifest   manifest
	definition struct {
		events  map[string]event.Type
		actions map[string]actions.Action
	}
}

var LogicController logicController

func (lc *logicController) Init() error {
	lc.definition.events = event.GetEventDefinitions()
	lc.definition.actions = actions.Registry
	err := lc.ParseManifest(defaultManifestYaml)
	if err != nil {
		return fmt.Errorf("parse manifest err: %w", err)
	}
	return nil
}

// Business logic is applied here
func (lc *logicController) HandleEvent(ctx context.Context, e event.Event) event.Reply {

	var performActionsRecursive func(ctx context.Context, actions []manifestAction) context.Context

	performActionsRecursive = func(ctx context.Context, actions []manifestAction) context.Context {
		for _, actionDeclaration := range actions {
			action, ok := lc.definition.actions[actionDeclaration.Name]
			if !ok {
				continue
			}
			actionWithModifier := actionDeclaration.Name
			if len(actionDeclaration.Modifier) > 0 {
				actionWithModifier += "(" + actionDeclaration.Modifier + ")"
			}
			logrus.Infof("[ACT] %v", actionWithModifier)

			var result bool
			var err error
			ctx, result, err = action.Perform(ctx, actionDeclaration.Modifier, e.Params)
			if err != nil {
				logrus.Errorf("action err (%v): %v", actionWithModifier, err)
			} else {
				getResultStr := func(result bool) string {
					if result {
						return "Success/True"
					} else {
						return "Error/False"
					}
				}
				logrus.Infof("[ACT] %v (=%v)", actionWithModifier, getResultStr(result))
			}
			if result {
				if len(actionDeclaration.ResultSuccessActions) > 0 {
					logrus.Infof("[ACT] %v (--> SUCCESS branch)", actionWithModifier)
					ctx = performActionsRecursive(ctx, actionDeclaration.ResultSuccessActions)
				} else if len(actionDeclaration.ResultTrueActions) > 0 {
					logrus.Infof("[ACT] %v (--> TRUE branch)", actionWithModifier)
					ctx = performActionsRecursive(ctx, actionDeclaration.ResultTrueActions)
				}
			} else {
				if len(actionDeclaration.ResultErrorActions) > 0 {
					logrus.Infof("[ACT] %v (--> ERROR branch)", actionWithModifier)
					ctx = performActionsRecursive(ctx, actionDeclaration.ResultErrorActions)
				} else if len(actionDeclaration.ResultFalseActions) > 0 {
					logrus.Infof("[ACT] %v (--> FALSE branch)", actionWithModifier)
					ctx = performActionsRecursive(ctx, actionDeclaration.ResultFalseActions)
				}
			}
		}
		return ctx
	}

	// This context will be returned from the call to PostEventSync().
	returnCtx := ctx

	for _, v := range lc.manifest.Events {
		evt, ok := lc.definition.events[v.Name]
		if ok && evt == e.Type {
			returnCtx = performActionsRecursive(ctx, v.Actions)
		}
	}

	return event.Reply{Ctx: returnCtx, Err: nil}
}
